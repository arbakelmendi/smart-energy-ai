"""Train an untuned Random Forest using training data and validate only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "energy_train.csv"
VALIDATION_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "energy_validation.csv"
FEATURE_SCHEMA_PATH = PROJECT_ROOT / "ml" / "results" / "feature_schema.json"
PHASE7_RESULTS_PATH = PROJECT_ROOT / "ml" / "results" / "phase7_validation_metrics.json"
RESULTS_PATH = PROJECT_ROOT / "ml" / "results" / "phase8_random_forest_validation_metrics.json"
CURRENT_APPLIANCES_COLUMN = "Appliances"
DATE_COLUMN = "date"


def _read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(f"Required metadata file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_split(
    frame: pd.DataFrame,
    split_name: str,
    feature_columns: list[str],
    target_column: str,
) -> None:
    expected_columns = [DATE_COLUMN, *feature_columns, target_column]
    if frame.columns.tolist() != expected_columns:
        raise ValueError(f"{split_name} columns do not match the feature schema order")
    if frame.empty:
        raise ValueError(f"{split_name} split is empty")
    if frame.isna().sum().sum():
        raise ValueError(f"{split_name} split contains missing values")
    if frame.duplicated().any() or frame[DATE_COLUMN].duplicated().any():
        raise ValueError(f"{split_name} split contains duplicate rows or timestamps")
    if not frame[DATE_COLUMN].is_monotonic_increasing:
        raise ValueError(f"{split_name} timestamps are not chronological")
    non_numeric = [
        column
        for column in feature_columns
        if not pd.api.types.is_numeric_dtype(frame[column])
    ]
    if non_numeric:
        raise TypeError(f"{split_name} features must be numeric: {non_numeric}")
    if not pd.api.types.is_numeric_dtype(frame[target_column]):
        raise TypeError(f"{split_name} target must be numeric")


def _metrics(actual: pd.Series, predicted: np.ndarray) -> dict[str, float]:
    actual_values = actual.to_numpy()
    return {
        "mae": float(mean_absolute_error(actual_values, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual_values, predicted))),
        "r2": float(r2_score(actual_values, predicted)),
    }


def run_phase8(
    train_path: Path = TRAIN_DATA_PATH,
    validation_path: Path = VALIDATION_DATA_PATH,
    feature_schema_path: Path = FEATURE_SCHEMA_PATH,
    phase7_results_path: Path = PHASE7_RESULTS_PATH,
    results_path: Path = RESULTS_PATH,
) -> tuple[dict[str, object], dict[str, object]]:
    """Fit Random Forest on training data and evaluate using validation data."""
    train_path = Path(train_path).resolve()
    validation_path = Path(validation_path).resolve()
    feature_schema_path = Path(feature_schema_path).resolve()
    phase7_results_path = Path(phase7_results_path).resolve()
    results_path = Path(results_path).resolve()

    for path in (train_path, validation_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required development split not found: {path}")

    schema = _read_json(feature_schema_path)
    phase7_checksum_before = _sha256_file(phase7_results_path)
    phase7_results = _read_json(phase7_results_path)
    date_column = schema.get("date_column")
    target_column = schema.get("target_column")
    feature_columns = schema.get("model_feature_columns")
    if date_column != DATE_COLUMN or not isinstance(target_column, str):
        raise ValueError("Feature schema has an unexpected date or target column")
    if not isinstance(feature_columns, list) or not all(
        isinstance(column, str) for column in feature_columns
    ):
        raise ValueError("Feature schema must define ordered model_feature_columns")
    if schema.get("number_of_model_features") != len(feature_columns):
        raise ValueError("Feature count does not match the ordered schema")
    if schema.get("forecast_horizon_minutes") != 10:
        raise ValueError("Expected the verified 10-minute forecast horizon")
    if DATE_COLUMN in feature_columns or target_column in feature_columns:
        raise ValueError("date and target must both be excluded from model inputs")
    if CURRENT_APPLIANCES_COLUMN not in feature_columns:
        raise ValueError("Current Appliances must remain a model input")

    if phase7_results.get("evaluation_split") != "validation":
        raise ValueError("Phase 7 reference metrics must be validation-only")
    if phase7_results.get("target") != target_column:
        raise ValueError("Phase 7 and feature schema targets do not match")
    if phase7_results.get("forecast_horizon_minutes") != schema["forecast_horizon_minutes"]:
        raise ValueError("Phase 7 and feature schema forecast horizons do not match")

    train = pd.read_csv(train_path, parse_dates=[DATE_COLUMN], float_precision="round_trip")
    validation = pd.read_csv(
        validation_path,
        parse_dates=[DATE_COLUMN],
        float_precision="round_trip",
    )
    _validate_split(train, "train", feature_columns, target_column)
    _validate_split(validation, "validation", feature_columns, target_column)

    expected_train_rows = phase7_results.get("train_rows")
    expected_validation_rows = phase7_results.get("validation_rows")
    if len(train) != expected_train_rows or len(validation) != expected_validation_rows:
        raise ValueError("Train/validation row counts differ from the Phase 7 metadata")
    if phase7_results.get("feature_count") != len(feature_columns):
        raise ValueError("Phase 7 feature count differs from feature_schema.json")
    if not train[DATE_COLUMN].max() < validation[DATE_COLUMN].min():
        raise ValueError("Training dates must precede validation dates")
    if not set(train[DATE_COLUMN]).isdisjoint(validation[DATE_COLUMN]):
        raise ValueError("Train and validation timestamps overlap")

    phase7_models = phase7_results.get("models")
    if not isinstance(phase7_models, dict):
        raise ValueError("Phase 7 results must contain its validation model metrics")
    persistence_reference = phase7_models.get("Persistence Baseline")
    linear_reference = phase7_models.get("Linear Regression")
    if not isinstance(persistence_reference, dict) or not isinstance(linear_reference, dict):
        raise ValueError("Phase 7 persistence and Linear Regression metrics are required")

    X_train = train.loc[:, feature_columns]
    y_train = train[target_column]
    X_validation = validation.loc[:, feature_columns]
    y_validation = validation[target_column]

    # This is an untuned pre-tuning baseline; only reproducibility settings are explicit.
    model = RandomForestRegressor(random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    predictions = model.predict(X_validation)
    random_forest_metrics = _metrics(y_validation, predictions)
    residuals = y_validation.to_numpy() - predictions

    comparisons = {
        "Persistence Baseline": {
            "mae": float(persistence_reference["mae"]),
            "rmse": float(persistence_reference["rmse"]),
            "r2": float(persistence_reference["r2"]),
        },
        "Linear Regression": {
            "mae": float(linear_reference["mae"]),
            "rmse": float(linear_reference["rmse"]),
            "r2": float(linear_reference["r2"]),
        },
        "Random Forest": random_forest_metrics,
    }
    current_best_model = min(comparisons, key=lambda name: comparisons[name]["rmse"])
    persistence_rmse = comparisons["Persistence Baseline"]["rmse"]
    linear_rmse = comparisons["Linear Regression"]["rmse"]
    if persistence_rmse <= 0 or linear_rmse <= 0:
        raise ValueError("Reference RMSE must be positive to calculate relative comparisons")

    resolved_parameters = model.get_params(deep=False)
    report: dict[str, object] = {
        "evaluation_split": "validation",
        "model": "Random Forest",
        "forecast_horizon_minutes": int(schema["forecast_horizon_minutes"]),
        "target": target_column,
        "train_rows": len(train),
        "validation_rows": len(validation),
        "feature_count": len(feature_columns),
        "random_state": 42,
        "resolved_random_forest_parameters": resolved_parameters,
        "mae": random_forest_metrics["mae"],
        "rmse": random_forest_metrics["rmse"],
        "r2": random_forest_metrics["r2"],
        "validation_model_comparison": comparisons,
        "current_best_validation_model_by_rmse": current_best_model,
        "random_forest_improvement_vs_persistence_percent": float(
            (persistence_rmse - random_forest_metrics["rmse"]) / persistence_rmse * 100
        ),
        "random_forest_improvement_vs_linear_regression_percent": float(
            (linear_rmse - random_forest_metrics["rmse"]) / linear_rmse * 100
        ),
        "mean_validation_residual": float(np.mean(residuals)),
        "std_validation_residual": float(np.std(residuals, ddof=1)),
        "scaling_applied": False,
        "hyperparameter_tuning_performed": False,
        "model_artifact_saved": False,
        "test_set_accessed": False,
        "note": "Test set was not loaded or evaluated in Phase 8.",
        "results_path": str(results_path),
    }

    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("w", encoding="utf-8", newline="\n") as results_file:
        json.dump(report, results_file, indent=2, sort_keys=True)
        results_file.write("\n")
    if _sha256_file(phase7_results_path) != phase7_checksum_before:
        raise RuntimeError("Phase 7 validation metrics changed during Phase 8")

    artifacts: dict[str, object] = {
        "validation_dates": validation[DATE_COLUMN].reset_index(drop=True),
        "actual": y_validation.reset_index(drop=True),
        "predictions": pd.Series(predictions),
        "residuals": pd.Series(residuals),
        "model": model,
        "results_path": results_path,
    }
    return report, artifacts


def main() -> None:
    report, _ = run_phase8()
    print(f"Evaluation split: {report['evaluation_split']}")
    print(f"Training rows: {report['train_rows']}")
    print(f"Validation rows: {report['validation_rows']}")
    print(f"Features: {report['feature_count']}")
    print(f"Random Forest random_state={report['random_state']}, n_jobs=-1")
    print(f"Resolved n_estimators: {report['resolved_random_forest_parameters']['n_estimators']}")
    print("Validation comparison (existing Phase 7 metrics are read, not recomputed):")
    for model_name, metrics in report["validation_model_comparison"].items():
        print(
            f"  {model_name}: MAE={metrics['mae']:.6f}, "
            f"RMSE={metrics['rmse']:.6f}, R2={metrics['r2']:.6f}"
        )
    print(f"Current best validation model by RMSE: {report['current_best_validation_model_by_rmse']}")
    print(
        "Random Forest RMSE improvement vs persistence: "
        f"{report['random_forest_improvement_vs_persistence_percent']:.6f}%"
    )
    print(
        "Random Forest RMSE improvement vs Linear Regression: "
        f"{report['random_forest_improvement_vs_linear_regression_percent']:.6f}%"
    )
    print(f"Mean validation residual: {report['mean_validation_residual']:.6f}")
    print(f"Std. dev. validation residual: {report['std_validation_residual']:.6f}")
    print("Scaling applied: False")
    print("Test set was not loaded or evaluated in Phase 8.")
    print(f"Validation metrics JSON: {report['results_path']}")


if __name__ == "__main__":
    main()