"""Deterministically persist the fixed Phase 11 model after its reproduction gate.

Only TRAIN + VALIDATION are fitted. TEST is used solely by the shared Phase 11
metric reproduction gate. Existing outputs must match deterministic regeneration.
"""
from __future__ import annotations

import json
import platform
from tempfile import TemporaryDirectory

import numpy as np
from xgboost import XGBRegressor

if __package__:
    from .explain_final_model import reconstruct_final_model
    from .evaluate_final_model import ROOT, RESULTS, load_split, read_json, sha256
    from .model_inference import ARTIFACT_PATH, METADATA_PATH, load_final_model, validate_feature_frame
else:
    from explain_final_model import reconstruct_final_model
    from evaluate_final_model import ROOT, RESULTS, load_split, read_json, sha256
    from model_inference import ARTIFACT_PATH, METADATA_PATH, load_final_model, validate_feature_frame

RESULT_PATH = RESULTS / "phase13_model_persistence.json"
VERIFICATION_ROWS = 128


def prediction_sha256(values):
    import hashlib
    # Stable binary representation; no large prediction arrays are tracked.
    return hashlib.sha256(np.asarray(values, dtype="<f4").tobytes()).hexdigest()


def json_bytes(payload):
    return (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def verify_existing(path, expected_bytes):
    if path.exists() and path.read_bytes() != expected_bytes:
        raise ValueError(f"Existing output differs from deterministic regeneration: {path.relative_to(ROOT)}; preserved")


def run_phase13():
    # Reuse Phase 12's locked reconstruction/equivalence helper only.
    # It never computes feature importance or updates Phase 10-12 outputs.
    model, _, _, reproduction, inputs, lock, dependencies = reconstruct_final_model()
    phase11 = read_json(RESULTS / "phase11_final_test_evaluation.json")
    for name in ("phase12_feature_importance.json", "phase12_reproducibility.json"):
        path = RESULTS / name
        inputs[path.relative_to(ROOT).as_posix()] = sha256(path)
    phase12 = read_json(RESULTS / "phase12_feature_importance.json")
    if (phase12["selected_hyperparameters"] != lock["selected_hyperparameters"]
        or phase12["feature_columns"] != lock["feature_columns"]
        or phase12["final_model_name"] != lock["final_model_name"]):
        raise ValueError("Phase 12 configuration does not match the final lock")
    schema = read_json(RESULTS / "feature_schema.json")
    splits = read_json(RESULTS / "split_metadata.json")
    train, _ = load_split("train", schema, splits)
    validation, _ = load_split("validation", schema, splits)
    for name, frame in (("train", train), ("validation", validation)):
        if len(frame) != phase11[f"{name}_rows"]:
            raise ValueError(f"{name} row count differs from Phase 11")
    # Deterministic development-only sample; TEST is not used for reload checks.
    sample = train.loc[:, schema["model_feature_columns"]].iloc[:VERIFICATION_ROWS].copy()
    validate_feature_frame(sample, lock["feature_columns"])
    before = model.predict(sample)
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".phase13-", dir=ARTIFACT_PATH.parent) as temporary:
        from pathlib import Path
        candidate = Path(temporary) / ARTIFACT_PATH.name
        model.save_model(candidate)  # Supported native JSON, never pickle/dump_model.
        loaded = XGBRegressor(**lock["selected_hyperparameters"])
        loaded.load_model(candidate)
        after = loaded.predict(sample)
        maximum_difference = float(np.max(np.abs(before.astype(float) - after.astype(float))))
        if not np.array_equal(before, after):
            raise AssertionError("Native model reload predictions differ; artifact not published")
        artifact_checksum = sha256(candidate)
        metadata = {
            "model_name": lock["final_model_name"], "model_family": "XGBoost",
            "model_format": "XGBoost native JSON", "xgboost_version": dependencies["xgboost"],
            "sklearn_version": dependencies["scikit-learn"], "python_version": platform.python_version(),
            "dependencies": dependencies, "forecast_horizon_minutes": schema["forecast_horizon_minutes"],
            "target_column": schema["target_column"], "prediction_unit": "Wh",
            "ordered_feature_names": schema["model_feature_columns"], "feature_count": 42,
            "locked_hyperparameters": lock["selected_hyperparameters"],
            "train_rows": len(train), "validation_rows": len(validation),
            "development_rows": phase11["development_rows"],
            "development_start_timestamp": phase11["development_start_timestamp"],
            "development_end_timestamp": phase11["development_end_timestamp"],
            "held_out_test_metrics_from_phase11": {k: phase11[f"test_{k}"] for k in ("mae", "rmse", "r2")},
            "performance_source": "ml/results/phase11_final_test_evaluation.json; authoritative final evaluation, not a new experiment",
            "model_selection_basis": lock["selection_basis"],
            "model_artifact_relative_path": ARTIFACT_PATH.relative_to(ROOT).as_posix(),
            "model_artifact_sha256": artifact_checksum,
            "feature_schema_sha256": sha256(RESULTS / "feature_schema.json"),
            "selection_lock_sha256": sha256(RESULTS / "phase11_selection_lock.json"),
            "input_sha256": inputs, "test_used_for_fitting": False,
            "training_statement": "TRAIN + VALIDATION only; TEST is excluded from fitting and used only for Phase 11 reproduction",
            "feature_contract": "Already-engineered real finite numeric DataFrame; exactly 42 features in committed order; no coercion, imputation or reordering",
            "serialization_reference": "https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html",
            "serialization_choice": "Explicit .json selects supported native JSON; UBJ is the default but JSON remains officially supported",
            "verification_sample": {"source": "First 128 chronological TRAIN rows", "rows": len(sample),
                "first_timestamp": train.date.iloc[0].isoformat(sep=" "),
                "last_timestamp": train.date.iloc[len(sample)-1].isoformat(sep=" "),
                "predictions_float32_le_sha256": prediction_sha256(before)},
        }
        metadata_content = json_bytes(metadata)
        import hashlib
        record = {
            "model_name": lock["final_model_name"], "model_format": metadata["model_format"],
            "artifact_path": metadata["model_artifact_relative_path"], "artifact_sha256": artifact_checksum,
            "metadata_path": METADATA_PATH.relative_to(ROOT).as_posix(),
            "metadata_sha256": hashlib.sha256(metadata_content).hexdigest(),
            "feature_count": 42, "target": schema["target_column"], "forecast_horizon_minutes": 10,
            "development_rows": phase11["development_rows"], "phase11_metric_reproduction": reproduction,
            "reload_verification": {"passed": True, "exact_prediction_equality": True,
                "verification_rows": len(sample), "max_absolute_prediction_difference_wh": maximum_difference,
                "sample": "First 128 chronological TRAIN rows; no TEST reload predictions"},
            "test_used_for_fitting": False, "tuning_performed": False, "model_selection_changed": False,
            "feature_selection_performed": False, "input_sha256": inputs, "input_checksums_unchanged": True,
            "regeneration_policy": "Rebuild candidate deterministically; require identical existing model/metadata/record before replacing anything; no numbered model copies",
        }
        # Validate every existing destination before publishing any new output.
        if ARTIFACT_PATH.exists() and sha256(ARTIFACT_PATH) != artifact_checksum:
            raise ValueError("Existing canonical artifact differs; preserved")
        verify_existing(METADATA_PATH, metadata_content)
        verify_existing(RESULT_PATH, json_bytes(record))
        if any(sha256(ROOT / p) != h for p, h in inputs.items()):
            raise RuntimeError("A source split or Phase 10-12 artifact changed")
        if not ARTIFACT_PATH.exists():
            candidate.replace(ARTIFACT_PATH)
        if not METADATA_PATH.exists():
            METADATA_PATH.write_bytes(metadata_content)
        bundle = load_final_model()
        if not np.array_equal(before, bundle[0].predict(sample)):
            raise AssertionError("Published model failed final reload verification")
        if not RESULT_PATH.exists():
            RESULT_PATH.write_bytes(json_bytes(record))
    return record


if __name__ == "__main__":
    print(json.dumps(run_phase13(), indent=2, sort_keys=True))
