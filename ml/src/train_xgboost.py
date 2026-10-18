"""Train an untuned XGBoost baseline on training data and validate only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "energy_train.csv"
VALIDATION_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "energy_validation.csv"
FEATURE_SCHEMA_PATH = PROJECT_ROOT / "ml" / "results" / "feature_schema.json"
PHASE7_RESULTS_PATH = PROJECT_ROOT / "ml" / "results" / "phase7_validation_metrics.json"
PHASE8_RESULTS_PATH = PROJECT_ROOT / "ml" / "results" / "phase8_random_forest_validation_metrics.json"
RESULTS_PATH = PROJECT_ROOT / "ml" / "results" / "phase9_xgboost_validation_metrics.json"
DATE_COLUMN = "date"
CURRENT_APPLIANCES_COLUMN = "Appliances"

# Standard XGBoost defaults are explicit so the pre-tuning configuration is recorded.
XGBOOST_PARAMETERS = {
    "n_estimators": 100,
    "learning_rate": 0.3,
    "max_depth": 6,
    "min_child_weight": 1,
    "subsample": 1.0,
    "colsample_bytree": 1.0,
    "reg_alpha": 0.0,
    "reg_lambda": 1.0,
    "objective": "reg:squarederror",
    "random_state": 42,
    "n_jobs": 1,
    "tree_method": "hist",
    "verbosity": 0,
}


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


def run_phase9(
    train_path: Path = TRAIN_DATA_PATH,
    validation_path: Path = VALIDATION_DATA_PATH,
    feature_schema_path: Path = FEATURE_SCHEMA_PATH,
    phase7_results_path: Path = PHASE7_RESULTS_PATH,
    phase8_results_path: Path = PHASE8_RESULTS_PATH,
    results_path: Path = RESULTS_PATH,
) -> tuple[dict[str, object], dict[str, object]]:
    """Fit XGBoost on train only and compute validation-only metrics."""
    train_path = Path(train_path).resolve()
    validation_path = Path(validation_path).resolve()
    feature_schema_path = Path(feature_schema_path).resolve()
    phase7_results_path = Path(phase7_results_path).resolve()
    phase8_results_path = Path(phase8_results_path).resolve()
    results_path = Path(results_path).resolve()

    for path in (train_path, validation_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required development split not found: {path}")

    phase7_checksum_before = _sha256_file(phase7_results_path)
    phase8_checksum_before = _sha256_file(phase8_results_path)
    schema = _read_json(feature_schema_path)
    phase7_results = _read_json(phase7_results_path)
    phase8_results = _read_json(phase8_results_path)
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
        raise ValueError("date and target must not be included in model inputs")
    if CURRENT_APPLIANCES_COLUMN not in feature_columns:
        raise ValueError("Current Appliances must remain a model input")

    for name, previous in (("Phase 7", phase7_results), ("Phase 8", phase8_results)):
        if previous.get("evaluation_split") != "validation":
            raise ValueError(f"{name} reference metrics must be validation-only")
        if previous.get("target") != target_column:
            raise ValueError(f"{name} reference target differs from feature schema")
        if previous.get("forecast_horizon_minutes") != schema["forecast_horizon_minutes"]:
            raise ValueError(f"{name} reference horizon differs from feature schema")
        if previous.get("feature_count") != len(feature_columns):
            raise ValueError(f"{name} reference feature count differs from feature schema")

    train = pd.read_csv(train_path, parse_dates=[DATE_COLUMN], float_precision="round_trip")
    validation = pd.read_csv(
        validation_path,
        parse_dates=[DATE_COLUMN],
        float_precision="round_trip",
    )
    _validate_split(train, "train", feature_columns, target_column)
    _validate_split(validation, "validation", feature_columns, target_column)

    for name, previous in (("Phase 7", phase7_results), ("Phase 8", phase8_results)):
        if len(train) != previous.get("train_rows"):
            raise ValueError(f"Train row count differs from {name} metrics")
        if len(validation) != previous.get("validation_rows"):
            raise ValueError(f"Validation row count differs from {name} metrics")
    if not train[DATE_COLUMN].max() < validation[DATE_COLUMN].min():
        raise ValueError("Training dates must precede validation dates")
    if not set(train[DATE_COLUMN]).isdisjoint(validation[DATE_COLUMN]):
        raise ValueError("Train and validation timestamps overlap")

    X_train = train.loc[:, feature_columns]
    y_train = train[target_column]
    X_validation = validation.loc[:, feature_columns]
    y_validation = validation[target_column]

    model = XGBRegressor(**XGBOOST_PARAMETERS)
    model.fit(X_train, y_train)
    predictions = model.predict(X_validation)
    xgboost_metrics = _metrics(y_validation, predictions)
    residuals = y_validation.to_numpy() - predictions

    phase7_models = phase7_results.get("models")
    phase8_comparison = phase8_results.get("validation_model_comparison")
    if not isinstance(phase7_models, dict) or not isinstance(phase8_comparison, dict):
        raise ValueError("Previous validation metrics are incomplete")
    persistence_metrics = phase7_models.get("Persistence Baseline")
    linear_metrics = phase7_models.get("Linear Regression")
    forest_metrics = phase8_comparison.get("Random Forest")
    if not all(isinstance(value, dict) for value in (persistence_metrics, linear_metrics, forest_metrics)):
        raise ValueError("Previous persistence, Linear Regression, and Random Forest metrics are required")

    comparison = {
        "Persistence Baseline": {
            "mae": float(persistence_metrics["mae"]),
            "rmse": float(persistence_metrics["rmse"]),
            "r2": float(persistence_metrics["r2"]),
        },
        "Linear Regression": {
            "mae": float(linear_metrics["mae"]),
            "rmse": float(linear_metrics["rmse"]),
            "r2": float(linear_metrics["r2"]),
        },
        "Random Forest": {
            "mae": float(forest_metrics["mae"]),
            "rmse": float(forest_metrics["rmse"]),
            "r2": float(forest_metrics["r2"]),
        },
        "XGBoost": xgboost_metrics,
    }
    current_best_model = min(comparison, key=lambda name: comparison[name]["rmse"])
    reference_rmse = {
        "persistence": comparison["Persistence Baseline"]["rmse"],
        "linear_regression": comparison["Linear Regression"]["rmse"],
        "random_forest": comparison["Random Forest"]["rmse"],
    }
    if any(value <= 0 for value in reference_rmse.values()):
        raise ValueError("Reference RMSE must be positive for relative comparisons")

    model_parameters = model.get_params(deep=False)
    resolved_parameter_names = (
        "n_estimators",
        "learning_rate",
        "max_depth",
        "min_child_weight",
        "subsample",
        "colsample_bytree",
        "reg_alpha",
        "reg_lambda",
        "objective",
        "random_state",
        "n_jobs",
        "tree_method",
        "verbosity",
        "enable_categorical",
    )
    resolved_parameters = {
        name: model_parameters[name] for name in resolved_parameter_names
    }
    report: dict[str, object] = {
        "evaluation_split": "validation",
        "model": "XGBoost",
        "forecast_horizon_minutes": int(schema["forecast_horizon_minutes"]),
        "target": target_column,
        "train_rows": len(train),
        "validation_rows": len(validation),
        "feature_count": len(feature_columns),
        "random_state": 42,
        "resolved_xgboost_parameters": resolved_parameters,
        "mae": xgboost_metrics["mae"],
        "rmse": xgboost_metrics["rmse"],
        "r2": xgboost_metrics["r2"],
        "validation_rmse": {
            "persistence": reference_rmse["persistence"],
            "linear_regression": reference_rmse["linear_regression"],
            "random_forest": reference_rmse["random_forest"],
            "xgboost": xgboost_metrics["rmse"],
        },
        "validation_model_comparison": comparison,
        "current_best_validation_model_by_rmse": current_best_model,
        "xgboost_rmse_improvement_vs_persistence_percent": float(
            (reference_rmse["persistence"] - xgboost_metrics["rmse"])
            / reference_rmse["persistence"]
            * 100
        ),
        "xgboost_rmse_improvement_vs_linear_regression_percent": float(
            (reference_rmse["linear_regression"] - xgboost_metrics["rmse"])
            / reference_rmse["linear_regression"]
            * 100
        ),
        "xgboost_rmse_improvement_vs_random_forest_percent": float(
            (reference_rmse["random_forest"] - xgboost_metrics["rmse"])
            / reference_rmse["random_forest"]
            * 100
        ),
        "mean_validation_residual": float(np.mean(residuals)),
        "std_validation_residual": float(np.std(residuals, ddof=1)),
        "scaling_applied": False,
        "hyperparameter_tuning_performed": False,
        "early_stopping_used": False,
        "model_artifact_saved": False,
        "test_set_accessed": False,
        "note": "Test set was not loaded or evaluated in Phase 9.",
        "results_path": str(results_path),
    }

    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("w", encoding="utf-8", newline="\n") as results_file:
        json.dump(report, results_file, indent=2, sort_keys=True, allow_nan=False)
        results_file.write("\n")

    if _sha256_file(phase7_results_path) != phase7_checksum_before:
        raise RuntimeError("Phase 7 validation metrics changed during Phase 9")
    if _sha256_file(phase8_results_path) != phase8_checksum_before:
        raise RuntimeError("Phase 8 validation metrics changed during Phase 9")

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
    report, _ = run_phase9()
    print(f"Evaluation split: {report['evaluation_split']}")
    print(f"Training rows: {report['train_rows']}")
    print(f"Validation rows: {report['validation_rows']}")
    print(f"Features: {report['feature_count']}")
    print("Resolved XGBoost parameters:")
    for parameter, value in report["resolved_xgboost_parameters"].items():
        print(f"  {parameter}: {value}")
    print("Validation comparison (earlier phase metrics are reused):")
    for model_name, metrics in report["validation_model_comparison"].items():
        print(
            f"  {model_name}: MAE={metrics['mae']:.6f}, "
            f"RMSE={metrics['rmse']:.6f}, R2={metrics['r2']:.6f}"
        )
    print(f"Current best validation model by RMSE: {report['current_best_validation_model_by_rmse']}")
    print(
        "XGBoost RMSE improvement vs persistence: "
        f"{report['xgboost_rmse_improvement_vs_persistence_percent']:.6f}%"
    )
    print(
        "XGBoost RMSE improvement vs Linear Regression: "
        f"{report['xgboost_rmse_improvement_vs_linear_regression_percent']:.6f}%"
    )
    print(
        "XGBoost RMSE improvement vs Random Forest: "
        f"{report['xgboost_rmse_improvement_vs_random_forest_percent']:.6f}%"
    )
    print(f"Mean validation residual: {report['mean_validation_residual']:.6f}")
    print(f"Std. dev. validation residual: {report['std_validation_residual']:.6f}")
    print("Scaling applied: False; tuning performed: False; early stopping used: False")
    print("Test set was not loaded or evaluated in Phase 9.")
    print(f"Validation metrics JSON: {report['results_path']}")


if __name__ == "__main__":
    main()