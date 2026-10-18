"""Compare persistence and Linear Regression on validation data only."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "energy_train.csv"
VALIDATION_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "energy_validation.csv"
FEATURE_SCHEMA_PATH = PROJECT_ROOT / "ml" / "results" / "feature_schema.json"
SPLIT_METADATA_PATH = PROJECT_ROOT / "ml" / "results" / "split_metadata.json"
RESULTS_PATH = PROJECT_ROOT / "ml" / "results" / "phase7_validation_metrics.json"
CURRENT_APPLIANCES_COLUMN = "Appliances"


def _read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(f"Required metadata file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def _validate_split(
    frame: pd.DataFrame,
    split_name: str,
    date_column: str,
    target_column: str,
    feature_columns: list[str],
) -> None:
    expected_columns = [date_column, *feature_columns, target_column]
    if frame.columns.tolist() != expected_columns:
        raise ValueError(
            f"{split_name} columns do not match feature_schema.json ordered schema"
        )
    if frame.empty:
        raise ValueError(f"{split_name} split is empty")
    if frame.isna().sum().sum():
        raise ValueError(f"{split_name} split contains missing values")
    if frame.duplicated().any():
        raise ValueError(f"{split_name} split contains duplicate rows")
    if frame[date_column].duplicated().any():
        raise ValueError(f"{split_name} split contains duplicate timestamps")
    if not frame[date_column].is_monotonic_increasing:
        raise ValueError(f"{split_name} timestamps are not chronological")
    non_numeric = [
        column
        for column in feature_columns
        if not pd.api.types.is_numeric_dtype(frame[column])
    ]
    if non_numeric:
        raise TypeError(f"{split_name} model features must be numeric: {non_numeric}")
    if not pd.api.types.is_numeric_dtype(frame[target_column]):
        raise TypeError(f"{split_name} target must be numeric")


def _validation_metrics(actual: pd.Series, predicted: np.ndarray) -> dict[str, float]:
    actual_values = actual.to_numpy()
    return {
        "mae": float(mean_absolute_error(actual_values, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual_values, predicted))),
        "r2": float(r2_score(actual_values, predicted)),
    }


def run_phase7(
    train_path: Path = TRAIN_DATA_PATH,
    validation_path: Path = VALIDATION_DATA_PATH,
    feature_schema_path: Path = FEATURE_SCHEMA_PATH,
    split_metadata_path: Path = SPLIT_METADATA_PATH,
    results_path: Path = RESULTS_PATH,
) -> tuple[dict[str, object], dict[str, object]]:
    """Fit on training only and compare both approaches on validation only."""
    train_path = Path(train_path).resolve()
    validation_path = Path(validation_path).resolve()
    feature_schema_path = Path(feature_schema_path).resolve()
    split_metadata_path = Path(split_metadata_path).resolve()
    results_path = Path(results_path).resolve()

    for path in (train_path, validation_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required development split not found: {path}")

    schema = _read_json(feature_schema_path)
    split_metadata = _read_json(split_metadata_path)
    date_column = schema.get("date_column")
    target_column = schema.get("target_column")
    feature_columns = schema.get("model_feature_columns")
    if not isinstance(date_column, str) or not isinstance(target_column, str):
        raise ValueError("Feature schema must define date_column and target_column")
    if not isinstance(feature_columns, list) or not all(
        isinstance(column, str) for column in feature_columns
    ):
        raise ValueError("Feature schema must define ordered model_feature_columns")
    if schema.get("number_of_model_features") != len(feature_columns):
        raise ValueError("Feature count in schema does not match model_feature_columns")
    if date_column in feature_columns:
        raise ValueError("Traceability date must not be included in model features")
    if target_column in feature_columns:
        raise ValueError("Supervised target must not be included in model features")
    if CURRENT_APPLIANCES_COLUMN not in feature_columns:
        raise ValueError("Current Appliances must remain an approved model input")

    train = pd.read_csv(train_path, parse_dates=[date_column], float_precision="round_trip")
    validation = pd.read_csv(
        validation_path,
        parse_dates=[date_column],
        float_precision="round_trip",
    )
    _validate_split(train, "train", date_column, target_column, feature_columns)
    _validate_split(validation, "validation", date_column, target_column, feature_columns)

    expected_train_rows = split_metadata.get("train_rows")
    expected_validation_rows = split_metadata.get("validation_rows")
    if len(train) != expected_train_rows:
        raise ValueError("Train row count does not match split_metadata.json")
    if len(validation) != expected_validation_rows:
        raise ValueError("Validation row count does not match split_metadata.json")
    if not train[date_column].max() < validation[date_column].min():
        raise ValueError("Training dates must precede validation dates")
    if not set(train[date_column]).isdisjoint(validation[date_column]):
        raise ValueError("Train and validation timestamps overlap")

    X_train = train.loc[:, feature_columns]
    y_train = train[target_column]
    X_validation = validation.loc[:, feature_columns]
    y_validation = validation[target_column]

    # Persistence uses the observed target component available at forecast origin t.
    persistence_predictions = validation[CURRENT_APPLIANCES_COLUMN].to_numpy(copy=True)
    persistence_metrics = _validation_metrics(y_validation, persistence_predictions)

    linear_pipeline = Pipeline(
        steps=[
            ("standard_scaler", StandardScaler()),
            ("linear_regression", LinearRegression()),
        ]
    )
    linear_pipeline.fit(X_train, y_train)
    scaler = linear_pipeline.named_steps["standard_scaler"]
    scaler_fit_rows = int(np.asarray(scaler.n_samples_seen_).max())
    scaler_mean_matches_training = bool(
        np.allclose(
            scaler.mean_,
            X_train.mean(axis=0).to_numpy(),
            rtol=1e-12,
            atol=1e-12,
        )
    )
    if scaler_fit_rows != len(X_train) or not scaler_mean_matches_training:
        raise AssertionError("StandardScaler was not fitted exclusively on X_train")

    linear_predictions = linear_pipeline.predict(X_validation)
    linear_metrics = _validation_metrics(y_validation, linear_predictions)
    residuals = y_validation.to_numpy() - linear_predictions
    if persistence_metrics["rmse"] <= 0:
        raise ValueError("Persistence RMSE must be positive to calculate relative improvement")
    rmse_improvement_percent = (
        (persistence_metrics["rmse"] - linear_metrics["rmse"])
        / persistence_metrics["rmse"]
        * 100
    )

    model_metrics = {
        "Persistence Baseline": persistence_metrics,
        "Linear Regression": linear_metrics,
    }
    best_model = min(model_metrics, key=lambda name: model_metrics[name]["rmse"])
    report: dict[str, object] = {
        "evaluation_split": "validation",
        "forecast_horizon_minutes": int(schema["forecast_horizon_minutes"]),
        "target": target_column,
        "train_rows": len(train),
        "validation_rows": len(validation),
        "feature_count": len(feature_columns),
        "models": model_metrics,
        "best_validation_model_by_rmse": best_model,
        "linear_regression_rmse_improvement_percent": float(rmse_improvement_percent),
        "linear_regression_mean_residual": float(np.mean(residuals)),
        "scaler_fit_split": "train",
        "scaler_fit_rows": scaler_fit_rows,
        "scaler_fit_mean_matches_training": scaler_mean_matches_training,
        "test_set_accessed": False,
        "note": "Test set was not loaded or evaluated in Phase 7.",
        "results_path": str(results_path),
    }

    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("w", encoding="utf-8", newline="\n") as results_file:
        json.dump(report, results_file, indent=2, sort_keys=True)
        results_file.write("\n")

    artifacts: dict[str, object] = {
        "validation_dates": validation[date_column].reset_index(drop=True),
        "actual": y_validation.reset_index(drop=True),
        "persistence_predictions": pd.Series(persistence_predictions),
        "linear_regression_predictions": pd.Series(linear_predictions),
        "linear_regression_residuals": pd.Series(residuals),
        "linear_pipeline": linear_pipeline,
        "results_path": results_path,
    }
    return report, artifacts


def main() -> None:
    report, _ = run_phase7()
    print(f"Evaluation split: {report['evaluation_split']}")
    print(f"Training rows: {report['train_rows']}")
    print(f"Validation rows: {report['validation_rows']}")
    print(f"Model features: {report['feature_count']}")
    print(f"Target: {report['target']}; horizon: {report['forecast_horizon_minutes']} minutes")
    print("Validation metrics:")
    for model_name, metrics in report["models"].items():
        print(
            f"  {model_name}: MAE={metrics['mae']:.6f}, "
            f"RMSE={metrics['rmse']:.6f}, R2={metrics['r2']:.6f}"
        )
    print(f"Best Phase 7 validation RMSE: {report['best_validation_model_by_rmse']}")
    print(
        "Linear Regression RMSE improvement over persistence: "
        f"{report['linear_regression_rmse_improvement_percent']:.6f}%"
    )
    print(f"Linear Regression validation mean residual: {report['linear_regression_mean_residual']:.6f}")
    print(
        "StandardScaler fit only on train: "
        f"{report['scaler_fit_split']} ({report['scaler_fit_rows']} rows)"
    )
    print("Test set was not loaded or evaluated in Phase 7.")
    print(f"Validation metrics JSON: {report['results_path']}")


if __name__ == "__main__":
    main()