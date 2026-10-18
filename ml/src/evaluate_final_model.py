"""Validation-only final selection, development refit, then held-out evaluation.

The first result is never overwritten. --verify-reproducibility permits only
an identical technical replay and checks exact predictions and metrics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "ml/results"
RESULT_PATH = RESULTS / "phase11_final_test_evaluation.json"
GENERATED = RESULTS / "generated"
PREDICTIONS_PATH = GENERATED / "phase11_test_predictions.csv"
LOCK_PATH = RESULTS / "phase11_selection_lock.json"
REPLAY_PATH = RESULTS / "phase11_reproducibility.json"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_new(path, payload):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def select_configuration():
    """A: no split data access; RMSE only, exact ties use stable model name."""
    summary = read_json(RESULTS / "phase10_tuning_summary.json")
    cv = read_json(RESULTS / "phase10_tuning_cv_results.json")
    p7 = read_json(RESULTS / "phase7_validation_metrics.json")
    p8 = read_json(RESULTS / "phase8_random_forest_validation_metrics.json")
    p9 = read_json(RESULTS / "phase9_xgboost_validation_metrics.json")
    comparison = summary["validation_model_comparison"]
    expected = {
        **p7["models"],
        "Untuned Random Forest": {k: p8[k] for k in ("mae", "rmse", "r2")},
        "Untuned XGBoost": {k: p9[k] for k in ("mae", "rmse", "r2")},
        "Tuned Random Forest": summary["random_forest"]["tuned_validation_metrics"],
        "Tuned XGBoost": summary["xgboost"]["tuned_validation_metrics"],
    }
    if comparison != expected or summary["test_set_accessed"]:
        raise ValueError("Inconsistent validation provenance")
    if any(not np.isfinite(list(m.values())).all() for m in comparison.values()):
        raise ValueError("Nonfinite validation metrics")
    ranking = sorted(comparison, key=lambda n: (comparison[n]["rmse"], n))
    name = ranking[0]
    if name.startswith("Tuned"):
        family = "xgboost" if name == "Tuned XGBoost" else "random_forest"
        record = summary[family]
        best = min(cv[family]["candidates"], key=lambda c: (c["mean_cv_rmse"], c["candidate_id"]))
        if record["best_parameters"] != best["parameters"]:
            raise ValueError("Selected parameters disagree with TRAIN CV audit")
        base = summary[family].get("base_parameters", {"random_state": record["random_state"], "n_jobs": 1})
        parameters = {**base, **record["best_parameters"]}
    elif name == "Untuned XGBoost":
        parameters = p9["resolved_xgboost_parameters"]
    elif name == "Untuned Random Forest":
        parameters = p8["resolved_random_forest_parameters"]
    else:
        parameters = {}  # Phase 7 defaults; scaler is refitted only on development.
    return {
        "final_model_name": name,
        "selected_hyperparameters": parameters,
        "selected_validation_metrics": comparison[name],
        "validation_ranking": [{"model": n, **comparison[n]} for n in ranking],
        "selection_basis": "Saved validation results only; lowest validation RMSE",
        "selection_metric": "validation_rmse",
        "tie_breaking_rule": "Exact RMSE ties: alphabetical model name; MAE and R2 are supporting only",
        "expected_tuned_xgboost_selected": name == "Tuned XGBoost",
        "selection_statement": "Final model selection was completed before accessing the held-out test set.",
    }


def instantiate(config):
    name, params = config["final_model_name"], config["selected_hyperparameters"]
    if "XGBoost" in name:
        return XGBRegressor(**params)
    if "Random Forest" in name:
        return RandomForestRegressor(**params)
    if name == "Linear Regression":
        return make_pipeline(StandardScaler(), LinearRegression())
    if name == "Persistence Baseline":
        return None
    raise ValueError(f"Unapproved model: {name}")


def load_split(name, schema, metadata):
    path = ROOT / f"data/processed/energy_{name}.csv"
    checksum = sha256(path)
    if checksum != metadata["split_csv_sha256"][name]:
        raise ValueError(f"{name}: checksum differs from Phase 6")
    frame = pd.read_csv(path, parse_dates=["date"], float_precision="round_trip")
    features, target = schema["model_feature_columns"], schema["target_column"]
    if frame.columns.tolist() != ["date", *features, target]:
        raise ValueError(f"{name}: schema order mismatch")
    if len(frame) != metadata[f"{name}_rows"] or frame.empty or frame.isna().any().any():
        raise ValueError(f"{name}: invalid rows or missing values")
    if frame.date.duplicated().any() or not frame.date.is_monotonic_increasing:
        raise ValueError(f"{name}: timestamps not unique and chronological")
    if not frame.date.diff().dropna().eq(pd.Timedelta(minutes=10)).all():
        raise ValueError(f"{name}: unexpected time interval")
    if not np.isfinite(frame[[*features, target]].to_numpy(dtype=float)).all():
        raise ValueError(f"{name}: nonfinite numerical data")
    for edge, value in (("start", frame.date.iloc[0]), ("end", frame.date.iloc[-1])):
        if value != pd.Timestamp(metadata[f"{name}_{edge}"]):
            raise ValueError(f"{name}: boundary differs from metadata")
    return frame, checksum


def run_phase11(verify_reproducibility=False):
    if RESULT_PATH.exists() and not verify_reproducibility:
        raise FileExistsError("Final result exists. Use saved results, or --verify-reproducibility for identical replay.")
    if verify_reproducibility and not RESULT_PATH.exists():
        raise FileNotFoundError("An original final result is required for replay")
    config = select_configuration()
    schema = read_json(RESULTS / "feature_schema.json")
    metadata = read_json(RESULTS / "split_metadata.json")
    features, target = schema["model_feature_columns"], schema["target_column"]
    if (len(features) != 42 or len(set(features)) != 42
        or schema["number_of_model_features"] != 42 or "Appliances" not in features
        or "date" in features or target in features or target != "target_appliances_next"
        or schema["forecast_horizon_minutes"] != 10):
        raise ValueError("Unexpected approved schema")
    sources = [RESULTS / n for n in (
        "feature_schema.json", "split_metadata.json", "phase7_validation_metrics.json",
        "phase8_random_forest_validation_metrics.json", "phase9_xgboost_validation_metrics.json",
        "phase10_tuning_summary.json", "phase10_tuning_cv_results.json")]
    checksums = {str(p.relative_to(ROOT)).replace("\\", "/"): sha256(p) for p in sources}
    dependencies = {p: version(p) for p in ("numpy", "pandas", "scikit-learn", "xgboost")}
    # B: configuration fixed before development fitting. No TEST file opened.
    train, train_hash = load_split("train", schema, metadata)
    validation, val_hash = load_split("validation", schema, metadata)
    if not train.date.iloc[-1] < validation.date.iloc[0]:
        raise ValueError("Train must precede validation without overlap")
    development = pd.concat([train, validation], ignore_index=True)
    if (len(development) != len(train) + len(validation) or development.date.duplicated().any()
        or not development.date.is_monotonic_increasing or development.isna().any().any()):
        raise ValueError("Invalid development concatenation")
    checksums.update({f"data/processed/energy_{n}.csv": h for n, h in (("train", train_hash), ("validation", val_hash))})
    lock = {**config, "feature_columns": features, "input_sha256_before_test": checksums,
            "expected_test_sha256_from_phase6": metadata["split_csv_sha256"]["test"],
            "dependencies": dependencies, "python_version": platform.python_version()}
    if LOCK_PATH.exists():
        if read_json(LOCK_PATH) != lock:
            raise ValueError("Configuration/data/environment changed since pre-test lock")
    else:
        write_new(LOCK_PATH, lock)
    original = read_json(RESULT_PATH) if verify_reproducibility else None
    if original and original["selection_lock_sha256"] != sha256(LOCK_PATH):
        raise ValueError("Original selection lock changed")
    model = instantiate(config)
    X_development, y_development = development.loc[:, features], development[target]
    if model is not None:
        model.fit(X_development, y_development)  # one fit; no eval_set/early stopping
    # C: FIRST TEST ACCESS (including checksum): selection locked AND refit complete.
    test, test_hash = load_split("test", schema, metadata)
    if not development.date.iloc[-1] < test.date.iloc[0]:
        raise ValueError("Development and TEST overlap")
    X_test, y_test = test.loc[:, features], test[target]
    predictions = model.predict(X_test) if model is not None else X_test["Appliances"].to_numpy()
    residuals = y_test.to_numpy() - predictions
    metrics = {"mae": float(mean_absolute_error(y_test, predictions)),
               "rmse": float(np.sqrt(mean_squared_error(y_test, predictions))),
               "r2": float(r2_score(y_test, predictions))}
    prediction_frame = pd.DataFrame({"date": test.date, "actual": y_test,
                                     "predicted": predictions, "residual": residuals})
    prediction_bytes = prediction_frame.to_csv(index=False, float_format="%.17g", date_format="%Y-%m-%dT%H:%M:%S").encode()
    checksums["data/processed/energy_test.csv"] = test_hash
    if any(sha256(ROOT / p) != h for p, h in checksums.items()):
        raise RuntimeError("An input changed during evaluation")
    delta = metrics["rmse"] - config["selected_validation_metrics"]["rmse"]
    report = {**config, "forecast_horizon_minutes": 10, "target": target, "feature_count": len(features),
              "train_rows": len(train), "validation_rows": len(validation), "development_rows": len(development),
              "test_rows": len(test), "development_start_timestamp": development.date.iloc[0].isoformat(sep=" "),
              "development_end_timestamp": development.date.iloc[-1].isoformat(sep=" "),
              "test_start_timestamp": test.date.iloc[0].isoformat(sep=" "),
              "test_end_timestamp": test.date.iloc[-1].isoformat(sep=" "),
              **{f"test_{k}": v for k, v in metrics.items()},
              "test_mean_residual": float(np.mean(residuals)),
              "test_residual_std": float(np.std(residuals, ddof=1)),
              "test_median_residual": float(np.median(residuals)),
              "residual_definition": "actual - predicted; standard deviation uses ddof=1",
              "test_rmse_minus_validation_rmse": delta,
              "test_rmse_change_percent": delta / config["selected_validation_metrics"]["rmse"] * 100,
              "generalization_description": "Test RMSE increased" if delta > 0 else "Test RMSE decreased" if delta < 0 else "Test RMSE unchanged",
              "input_sha256": checksums, "input_checksums_unchanged": True,
              "selection_lock_sha256": sha256(LOCK_PATH),
              "predictions_sha256": hashlib.sha256(prediction_bytes).hexdigest(),
              "dependencies": dependencies, "python_version": platform.python_version(),
              "test_evaluation_count": 1,
              "evaluation_count_definition": "One final experimental workflow; identical technical replay is recorded separately",
              "test_access_point": "run_phase11 section C: load_split(test), only after configuration lock and development fit",
              "test_influenced_model_selection": False, "post_test_tuning_performed": False,
              "post_test_statement": "No post-test tuning was performed; test performance did not influence model selection.",
              "alternative_candidates_evaluated_on_test": False, "model_artifact_saved": False,
              "early_stopping_used": False, "feature_columns": features}
    if verify_reproducibility:
        if report != original:
            raise AssertionError("Exact replay differs from original final evaluation")
        if PREDICTIONS_PATH.exists() and sha256(PREDICTIONS_PATH) != report["predictions_sha256"]:
            raise AssertionError("Original saved predictions changed")
        replay = {"exact_metrics_reproduced": True, "exact_predictions_reproduced": True,
                  "identical_configuration_inputs_dependencies": True,
                  "original_result_sha256": sha256(RESULT_PATH),
                  "note": "Identical technical replay only; no new selection or tuning decisions"}
        if REPLAY_PATH.exists():
            if read_json(REPLAY_PATH) != replay:
                raise AssertionError("Reproducibility record changed")
        else:
            write_new(REPLAY_PATH, replay)
    else:
        GENERATED.mkdir(parents=True, exist_ok=True)
        with PREDICTIONS_PATH.open("xb") as stream:
            stream.write(prediction_bytes)
        write_new(RESULT_PATH, report)
    return report, prediction_frame


def load_saved_evaluation():
    """Notebook consumes the original result without fitting or test CSV access."""
    report = read_json(RESULT_PATH)
    if sha256(PREDICTIONS_PATH) != report["predictions_sha256"]:
        raise ValueError("Saved predictions do not match original evaluation")
    return report, pd.read_csv(PREDICTIONS_PATH, parse_dates=["date"], float_precision="round_trip")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-reproducibility", action="store_true")
    args = parser.parse_args()
    result, _ = run_phase11(args.verify_reproducibility)
    print(json.dumps(result, indent=2, sort_keys=True))
