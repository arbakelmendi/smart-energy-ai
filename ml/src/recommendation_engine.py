"""Development-calibrated, deterministic forecast-based decision support.

No fitting, test-data access, causal attribution, control or savings estimation.
"""
from __future__ import annotations

from numbers import Real
import json

import numpy as np
import pandas as pd

if __package__:
    from . import model_inference as inference
    from .evaluate_final_model import load_split
else:
    import model_inference as inference
    from evaluate_final_model import load_split

ROOT = inference.ROOT
THRESHOLD_PATH = ROOT / "ml/results/phase14_recommendation_thresholds.json"
LEVELS = {
    "NORMAL": "prediction < percentile_75",
    "ELEVATED": "percentile_75 <= prediction < percentile_90",
    "HIGH": "percentile_90 <= prediction < percentile_95",
    "VERY HIGH": "prediction >= percentile_95",
}
RULES = {
    "NORMAL": ("NORMAL_CONSUMPTION", "low", "No high-consumption warning",
               "No immediate high-consumption warning is detected for the upcoming 10-minute period."),
    "ELEVATED": ("ELEVATED_CONSUMPTION", "medium", "Review flexible loads",
                 "Review flexible or non-essential electrical loads where operationally appropriate for the upcoming 10-minute period."),
    "HIGH": ("HIGH_CONSUMPTION", "high", "Review discretionary demand",
             "Check whether discretionary loads can be delayed or reduced during the upcoming 10-minute period, if safe and operationally feasible."),
    "VERY HIGH": ("VERY_HIGH_CONSUMPTION", "high", "Unusually high forecast consumption",
                  "Predicted appliance consumption is unusually high relative to the development-data distribution. Review controllable, non-critical loads for the upcoming 10-minute period only if safe and operationally feasible."),
}
SCOPE_NOTE = ("Forecast-based decision support only. No automatic equipment control, causal sensor attribution, "
              "or guaranteed savings. Keep essential equipment operating safely. Forecasts may be inaccurate.")


def _number(value, name, nonnegative=False):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a real finite number")
    result = float(value)
    if not np.isfinite(result) or (nonnegative and result < 0):
        raise ValueError(f"{name} must be finite" + (" and nonnegative" if nonnegative else ""))
    return result


def development_data():
    """Load exactly the two Phase 6 development splits, verifying their checksums."""
    schema = inference.read_json(ROOT / "ml/results/feature_schema.json")
    splits = inference.read_json(ROOT / "ml/results/split_metadata.json")
    train, _ = load_split("train", schema, splits)
    validation, _ = load_split("validation", schema, splits)
    if not train.date.iloc[-1] < validation.date.iloc[0]:
        raise ValueError("Development forecast origins overlap")
    development = pd.concat([train, validation], ignore_index=True)
    inference.validate_feature_frame(development[schema["model_feature_columns"]])
    if (development["target_appliances_next"] < 0).any() or (development.Appliances < 0).any():
        raise ValueError("Development energy must be nonnegative")
    return development


def calibrate_thresholds():
    """Compute NumPy linear percentiles from TRAIN + VALIDATION targets only."""
    paths = [ROOT / f"data/processed/energy_{name}.csv" for name in ("train", "validation")]
    before = {p.relative_to(ROOT).as_posix(): inference.sha256(p) for p in paths}
    development = development_data()
    values = np.percentile(development.target_appliances_next.to_numpy(), [50, 75, 90, 95], method="linear")
    if before != {p.relative_to(ROOT).as_posix(): inference.sha256(p) for p in paths}:
        raise RuntimeError("Calibration inputs changed while reading")
    metadata = {
        "schema_version": 1, "calibration_dataset": "train+validation",
        "calibration_rows": len(development), "target_column": "target_appliances_next",
        "forecast_horizon_minutes": 10, "unit": "Wh", "percentile_method": "numpy.percentile(method=linear)",
        **{f"percentile_{p}": float(v) for p, v in zip((50, 75, 90, 95), values)},
        "level_definitions": LEVELS.copy(), "test_used": False,
        "test_usage_statement": "TEST was not opened or used for threshold calibration or rule design.",
        "calibration_input_sha256": before,
    }
    return validate_thresholds(metadata)


def validate_thresholds(metadata):
    if not isinstance(metadata, dict):
        raise ValueError("Threshold metadata must be an object")
    required = {"schema_version": 1, "calibration_dataset": "train+validation",
                "target_column": "target_appliances_next", "forecast_horizon_minutes": 10,
                "unit": "Wh", "percentile_method": "numpy.percentile(method=linear)",
                "level_definitions": LEVELS, "test_used": False}
    if any(metadata.get(k) != v for k, v in required.items()) or metadata.get("test_used") is not False:
        raise ValueError("Invalid threshold metadata contract")
    rows = metadata.get("calibration_rows")
    if type(rows) is not int or rows <= 0:
        raise ValueError("Invalid calibration row count")
    values = [_number(metadata.get(f"percentile_{p}"), f"percentile_{p}", True) for p in (50, 75, 90, 95)]
    if values != sorted(values):
        raise ValueError("Threshold percentiles must be nondecreasing")
    hashes = metadata.get("calibration_input_sha256", {})
    expected = {f"data/processed/energy_{name}.csv" for name in ("train", "validation")}
    if not isinstance(hashes, dict) or set(hashes) != expected:
        raise ValueError("Threshold provenance must contain only TRAIN + VALIDATION inputs")
    for value in hashes.values():
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("Invalid calibration checksum")
    return metadata


def load_thresholds(path=THRESHOLD_PATH):
    """Fail if calibration metadata is absent; never invent fallback thresholds."""
    return validate_thresholds(inference.read_json(path))


def recommend(predicted_appliances_wh, current_appliances_wh, *, thresholds=None):
    """Return a JSON-safe rule result. Negative forecasts are rejected, never clipped.

    Trend is the exact sign of forecast minus current energy: zero is stable.
    Equal percentiles are allowed; any resulting empty band is skipped naturally.
    """
    predicted = _number(predicted_appliances_wh, "prediction", True)
    current = _number(current_appliances_wh, "current energy", True)
    metadata = load_thresholds() if thresholds is None else validate_thresholds(thresholds)
    cuts = {f"percentile_{p}": float(metadata[f"percentile_{p}"]) for p in (50, 75, 90, 95)}
    level = ("NORMAL" if predicted < cuts["percentile_75"] else
             "ELEVATED" if predicted < cuts["percentile_90"] else
             "HIGH" if predicted < cuts["percentile_95"] else "VERY HIGH")
    code, priority, title, message = RULES[level]
    change = predicted - current
    percent = _number(change / current * 100, "change percent") if current > 0 else None
    return {
        "prediction": {"value_wh": predicted, "horizon_minutes": 10, "unit": "Wh", "level": level},
        "thresholds_wh": cuts,
        "trend": {"current_wh": current, "change_wh": change, "change_percent": percent,
                  "direction": "rising" if change > 0 else "falling" if change < 0 else "stable"},
        "recommendation": {"code": code, "priority": priority, "title": title, "message": message,
                           "rationale": f"Forecast {predicted:g} Wh satisfies {LEVELS[level]} using TRAIN + VALIDATION target percentiles; thresholds are in thresholds_wh."},
        "scope": {"automatic_control": False, "estimated_savings": None, "note": SCOPE_NOTE},
    }


def predict_and_recommend(feature_frame, *, model_bundle=None, thresholds=None):
    """Return one result per engineered row, in input order (also for one row).

    Reuses the persisted model and existing strict inference contract. The caller
    must supply current readings and valid history; no raw feature creation occurs.
    """
    inference.validate_feature_frame(feature_frame)
    if (feature_frame.Appliances < 0).any():
        raise ValueError("Current energy must be nonnegative")
    metadata = load_thresholds() if thresholds is None else validate_thresholds(thresholds)
    predictions = inference.predict_next_appliances(feature_frame, model_bundle)
    return [recommend(p, c, thresholds=metadata)
            for p, c in zip(predictions.to_numpy(), feature_frame.Appliances.to_numpy())]


def write_thresholds():
    metadata = calibrate_thresholds()
    THRESHOLD_PATH.write_text(json.dumps(metadata, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return metadata


if __name__ == "__main__":
    print(json.dumps(write_thresholds(), indent=2, sort_keys=True))
