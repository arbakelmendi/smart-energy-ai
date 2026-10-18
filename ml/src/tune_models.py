"""Tune tree models with chronological CV on TRAIN; evaluate selected models once."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from xgboost import XGBRegressor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "energy_train.csv"
VALIDATION_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "energy_validation.csv"
FEATURE_SCHEMA_PATH = PROJECT_ROOT / "ml" / "results" / "feature_schema.json"
PHASE7_RESULTS_PATH = PROJECT_ROOT / "ml" / "results" / "phase7_validation_metrics.json"
PHASE8_RESULTS_PATH = PROJECT_ROOT / "ml" / "results" / "phase8_random_forest_validation_metrics.json"
PHASE9_RESULTS_PATH = PROJECT_ROOT / "ml" / "results" / "phase9_xgboost_validation_metrics.json"
CV_RESULTS_PATH = PROJECT_ROOT / "ml" / "results" / "phase10_tuning_cv_results.json"
SUMMARY_RESULTS_PATH = PROJECT_ROOT / "ml" / "results" / "phase10_tuning_summary.json"
DATE_COLUMN = "date"
CV_SPLITS = 5
CV_SCORING = "neg_root_mean_squared_error"
RANDOM_STATE = 42
XGBOOST_BASE_PARAMETERS = {
    "objective": "reg:squarederror",
    "random_state": RANDOM_STATE,
    "n_jobs": 1,
    "tree_method": "hist",
    "verbosity": 0,
}

RANDOM_FOREST_PARAMETER_GRID = {
    "n_estimators": [100, 300],
    "max_depth": [None, 10, 20],
    "min_samples_leaf": [1, 2, 4],
    "max_features": [1.0, "sqrt"],
}

# Fixed before observing CV or validation results: eight balanced profiles,
# each tested at both requested estimator counts (16 total candidates).
_XGBOOST_PARAMETER_PROFILES = (
    (0.03, 3, 1, 0.8, 0.8),
    (0.03, 3, 5, 1.0, 1.0),
    (0.03, 6, 1, 1.0, 0.8),
    (0.03, 6, 5, 0.8, 1.0),
    (0.1, 3, 1, 1.0, 1.0),
    (0.1, 3, 5, 0.8, 0.8),
    (0.1, 6, 1, 0.8, 1.0),
    (0.1, 6, 5, 1.0, 0.8),
)
XGBOOST_CANDIDATES = tuple(
    {
        "n_estimators": n_estimators,
        "learning_rate": learning_rate,
        "max_depth": max_depth,
        "min_child_weight": min_child_weight,
        "subsample": subsample,
        "colsample_bytree": colsample_bytree,
    }
    for n_estimators in (100, 300)
    for (
        learning_rate,
        max_depth,
        min_child_weight,
        subsample,
        colsample_bytree,
    ) in _XGBOOST_PARAMETER_PROFILES
)


def _read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(f"Required results/metadata file not found: {path}")
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
    name: str,
    feature_columns: list[str],
    target_column: str,
) -> None:
    expected_columns = [DATE_COLUMN, *feature_columns, target_column]
    if frame.columns.tolist() != expected_columns:
        raise ValueError(f"{name} columns do not match feature_schema.json order")
    if frame.empty:
        raise ValueError(f"{name} split is empty")
    if frame.isna().sum().sum():
        raise ValueError(f"{name} split contains missing values")
    if frame.duplicated().any() or frame[DATE_COLUMN].duplicated().any():
        raise ValueError(f"{name} split contains duplicate rows or timestamps")
    if not frame[DATE_COLUMN].is_monotonic_increasing:
        raise ValueError(f"{name} dates are not chronological")
    non_numeric = [
        column
        for column in feature_columns
        if not pd.api.types.is_numeric_dtype(frame[column])
    ]
    if non_numeric:
        raise TypeError(f"{name} model features must be numeric: {non_numeric}")
    if not pd.api.types.is_numeric_dtype(frame[target_column]):
        raise TypeError(f"{name} target must be numeric")


def _metric_values(actual: pd.Series, predicted: np.ndarray) -> dict[str, float]:
    actual_values = actual.to_numpy()
    return {
        "mae": float(mean_absolute_error(actual_values, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual_values, predicted))),
        "r2": float(r2_score(actual_values, predicted)),
    }


def _candidate_records(
    cv_results: dict[str, object],
    fold_count: int,
) -> list[dict[str, object]]:
    params_list = cv_results["params"]
    mean_scores = cv_results["mean_test_score"]
    std_scores = cv_results["std_test_score"]
    records = []
    for candidate_index, parameters in enumerate(params_list):
        fold_rmse = [
            float(-cv_results[f"split{fold_index}_test_score"][candidate_index])
            for fold_index in range(fold_count)
        ]
        mean_cv_rmse = float(-mean_scores[candidate_index])
        std_cv_rmse = float(std_scores[candidate_index])
        if not np.isfinite(mean_cv_rmse) or not np.isfinite(std_cv_rmse):
            raise ValueError(f"Candidate {candidate_index} produced non-finite CV RMSE")
        records.append(
            {
                "candidate_id": candidate_index,
                "parameters": dict(parameters),
                "fold_rmse": fold_rmse,
                "mean_cv_rmse": mean_cv_rmse,
                "std_cv_rmse": std_cv_rmse,
            }
        )
    return records


def _run_search(
    estimator: object,
    parameter_grid: dict[str, list[object]] | list[dict[str, list[object]]],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cv_splits: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    search = GridSearchCV(
        estimator=estimator,
        param_grid=parameter_grid,
        scoring=CV_SCORING,
        cv=cv_splits,
        refit=False,
        n_jobs=1,
        return_train_score=False,
        error_score="raise",
    )
    search.fit(X_train, y_train)
    candidates = _candidate_records(search.cv_results_, len(cv_splits))
    best_index = min(
        range(len(candidates)),
        key=lambda index: candidates[index]["mean_cv_rmse"],
    )
    return candidates[best_index], candidates


def _fold_metadata(
    train: pd.DataFrame,
    cv_splits: list[tuple[np.ndarray, np.ndarray]],
) -> list[dict[str, object]]:
    folds = []
    for fold_number, (fit_indices, scoring_indices) in enumerate(cv_splits, start=1):
        fit_dates = train[DATE_COLUMN].iloc[fit_indices]
        scoring_dates = train[DATE_COLUMN].iloc[scoring_indices]
        chronological = bool(fit_dates.max() < scoring_dates.min())
        if not chronological:
            raise AssertionError(f"TimeSeriesSplit fold {fold_number} is not past-to-future")
        folds.append(
            {
                "fold": fold_number,
                "fit_rows": len(fit_indices),
                "scoring_rows": len(scoring_indices),
                "fit_start": fit_dates.min().isoformat(sep=" "),
                "fit_end": fit_dates.max().isoformat(sep=" "),
                "scoring_start": scoring_dates.min().isoformat(sep=" "),
                "scoring_end": scoring_dates.max().isoformat(sep=" "),
                "fit_precedes_scoring": chronological,
            }
        )
    return folds


def run_phase10(
    train_path: Path = TRAIN_DATA_PATH,
    validation_path: Path = VALIDATION_DATA_PATH,
    feature_schema_path: Path = FEATURE_SCHEMA_PATH,
    phase7_results_path: Path = PHASE7_RESULTS_PATH,
    phase8_results_path: Path = PHASE8_RESULTS_PATH,
    phase9_results_path: Path = PHASE9_RESULTS_PATH,
    cv_results_path: Path = CV_RESULTS_PATH,
    summary_results_path: Path = SUMMARY_RESULTS_PATH,
) -> tuple[dict[str, object], dict[str, object]]:
    """Tune tree models with TRAIN-only CV, then evaluate selected models once."""
    train_path = Path(train_path).resolve()
    validation_path = Path(validation_path).resolve()
    feature_schema_path = Path(feature_schema_path).resolve()
    phase7_results_path = Path(phase7_results_path).resolve()
    phase8_results_path = Path(phase8_results_path).resolve()
    phase9_results_path = Path(phase9_results_path).resolve()
    cv_results_path = Path(cv_results_path).resolve()
    summary_results_path = Path(summary_results_path).resolve()

    for path in (train_path, validation_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required development split not found: {path}")

    previous_paths = {
        "phase7": phase7_results_path,
        "phase8": phase8_results_path,
        "phase9": phase9_results_path,
    }
    previous_checksums = {name: _sha256_file(path) for name, path in previous_paths.items()}
    schema = _read_json(feature_schema_path)
    phase7 = _read_json(phase7_results_path)
    phase8 = _read_json(phase8_results_path)
    phase9 = _read_json(phase9_results_path)

    date_column = schema.get("date_column")
    target_column = schema.get("target_column")
    feature_columns = schema.get("model_feature_columns")
    if date_column != DATE_COLUMN or not isinstance(target_column, str):
        raise ValueError("Feature schema date or target column is invalid")
    if not isinstance(feature_columns, list) or not all(
        isinstance(column, str) for column in feature_columns
    ):
        raise ValueError("Feature schema must define ordered model_feature_columns")
    if schema.get("number_of_model_features") != len(feature_columns):
        raise ValueError("Feature count does not match the schema column list")
    if schema.get("forecast_horizon_minutes") != 10:
        raise ValueError("Expected a 10-minute forecast horizon")
    if DATE_COLUMN in feature_columns or target_column in feature_columns:
        raise ValueError("date and target must not be included in X")
    if "Appliances" not in feature_columns:
        raise ValueError("Current Appliances must remain in X")

    previous_results = {"phase7": phase7, "phase8": phase8, "phase9": phase9}
    for phase_name, previous in previous_results.items():
        if previous.get("evaluation_split") != "validation":
            raise ValueError(f"{phase_name} reference results are not validation-only")
        if previous.get("target") != target_column:
            raise ValueError(f"{phase_name} target differs from feature schema")
        if previous.get("forecast_horizon_minutes") != schema["forecast_horizon_minutes"]:
            raise ValueError(f"{phase_name} horizon differs from feature schema")
        if previous.get("train_rows") != phase7.get("train_rows"):
            raise ValueError(f"{phase_name} train row count differs from Phase 7")
        if previous.get("validation_rows") != phase7.get("validation_rows"):
            raise ValueError(f"{phase_name} validation row count differs from Phase 7")
        if previous.get("feature_count") != len(feature_columns):
            raise ValueError(f"{phase_name} feature count differs from schema")

    train = pd.read_csv(train_path, parse_dates=[DATE_COLUMN], float_precision="round_trip")
    validation = pd.read_csv(
        validation_path,
        parse_dates=[DATE_COLUMN],
        float_precision="round_trip",
    )
    _validate_split(train, "train", feature_columns, target_column)
    _validate_split(validation, "validation", feature_columns, target_column)
    if len(train) != phase7["train_rows"] or len(validation) != phase7["validation_rows"]:
        raise ValueError("Input split row counts do not match previous phase metadata")
    if not train[DATE_COLUMN].max() < validation[DATE_COLUMN].min():
        raise ValueError("Training data must precede the main validation data")
    if not set(train[DATE_COLUMN]).isdisjoint(validation[DATE_COLUMN]):
        raise ValueError("Training and validation timestamps overlap")

    X_train = train.loc[:, feature_columns]
    y_train = train[target_column]
    X_validation = validation.loc[:, feature_columns]
    y_validation = validation[target_column]

    splitter = TimeSeriesSplit(n_splits=CV_SPLITS)
    cv_splits = list(splitter.split(X_train))
    if len(cv_splits) != CV_SPLITS:
        raise AssertionError("TimeSeriesSplit generated an unexpected fold count")
    folds = _fold_metadata(train, cv_splits)

    rf_base = RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=-1)
    rf_best_cv, rf_candidates = _run_search(
        rf_base,
        RANDOM_FOREST_PARAMETER_GRID,
        X_train,
        y_train,
        cv_splits,
    )

    xgb_parameter_grid = [
        {name: [value] for name, value in candidate.items()}
        for candidate in XGBOOST_CANDIDATES
    ]
    xgb_base = XGBRegressor(**XGBOOST_BASE_PARAMETERS)
    xgb_best_cv, xgb_candidate_results = _run_search(
        xgb_base,
        xgb_parameter_grid,
        X_train,
        y_train,
        cv_splits,
    )

    # Hyperparameters are selected exclusively by mean TRAIN CV RMSE.
    tuned_rf = RandomForestRegressor(
        random_state=RANDOM_STATE,
        n_jobs=-1,
        **rf_best_cv["parameters"],
    )
    tuned_rf.fit(X_train, y_train)
    rf_validation_predictions = tuned_rf.predict(X_validation)
    tuned_rf_validation_metrics = _metric_values(y_validation, rf_validation_predictions)

    tuned_xgb = XGBRegressor(
        **XGBOOST_BASE_PARAMETERS,
        **xgb_best_cv["parameters"],
    )
    tuned_xgb.fit(X_train, y_train)
    xgb_validation_predictions = tuned_xgb.predict(X_validation)
    tuned_xgb_validation_metrics = _metric_values(y_validation, xgb_validation_predictions)

    untuned_rf = {key: float(phase8[key]) for key in ("mae", "rmse", "r2")}
    untuned_xgb = {key: float(phase9[key]) for key in ("mae", "rmse", "r2")}
    phase7_models = phase7.get("models")
    if not isinstance(phase7_models, dict):
        raise ValueError("Phase 7 results are missing baseline metrics")
    persistence_metrics = phase7_models.get("Persistence Baseline")
    linear_metrics = phase7_models.get("Linear Regression")
    if not isinstance(persistence_metrics, dict) or not isinstance(linear_metrics, dict):
        raise ValueError("Phase 7 persistence and Linear Regression metrics are required")

    validation_comparison = {
        "Persistence Baseline": {
            key: float(persistence_metrics[key]) for key in ("mae", "rmse", "r2")
        },
        "Linear Regression": {
            key: float(linear_metrics[key]) for key in ("mae", "rmse", "r2")
        },
        "Untuned Random Forest": untuned_rf,
        "Tuned Random Forest": tuned_rf_validation_metrics,
        "Untuned XGBoost": untuned_xgb,
        "Tuned XGBoost": tuned_xgb_validation_metrics,
    }
    current_best_model = min(
        validation_comparison,
        key=lambda name: validation_comparison[name]["rmse"],
    )
    best_before_tuning = min(
        {
            "Persistence Baseline": validation_comparison["Persistence Baseline"],
            "Linear Regression": validation_comparison["Linear Regression"],
            "Untuned Random Forest": validation_comparison["Untuned Random Forest"],
            "Untuned XGBoost": validation_comparison["Untuned XGBoost"],
        },
        key=lambda name: validation_comparison[name]["rmse"],
    )

    rf_improvement = (
        (untuned_rf["rmse"] - tuned_rf_validation_metrics["rmse"])
        / untuned_rf["rmse"]
        * 100
    )
    xgb_improvement = (
        (untuned_xgb["rmse"] - tuned_xgb_validation_metrics["rmse"])
        / untuned_xgb["rmse"]
        * 100
    )
    cv_results = {
        "methodology": "TRAIN-only TimeSeriesSplit with expanding windows; no shuffle",
        "n_splits": CV_SPLITS,
        "primary_selection_metric": "mean_cv_rmse",
        "scoring": CV_SCORING,
        "feature_count": len(feature_columns),
        "train_rows": len(train),
        "validation_rows": len(validation),
        "folds": folds,
        "random_forest": {
            "candidate_count": len(rf_candidates),
            "search_space": RANDOM_FOREST_PARAMETER_GRID,
            "candidates": rf_candidates,
        },
        "xgboost": {
            "candidate_count": len(xgb_candidate_results),
            "base_parameters": XGBOOST_BASE_PARAMETERS,
            "fixed_candidate_configurations": list(XGBOOST_CANDIDATES),
            "candidates": xgb_candidate_results,
        },
    }
    summary = {
        "evaluation_methodology": "5-fold expanding TimeSeriesSplit on TRAIN; select each tree model by lowest mean CV RMSE, refit on all TRAIN, evaluate once on VALIDATION",
        "cv_n_splits": CV_SPLITS,
        "primary_tuning_metric": "mean_cv_rmse",
        "feature_count": len(feature_columns),
        "train_rows": len(train),
        "validation_rows": len(validation),
        "cv_fold_boundaries": folds,
        "random_forest": {
            "candidate_count": len(rf_candidates),
            "untuned_validation_metrics": untuned_rf,
            "best_parameters": rf_best_cv["parameters"],
            "best_mean_cv_rmse": rf_best_cv["mean_cv_rmse"],
            "best_cv_rmse_std": rf_best_cv["std_cv_rmse"],
            "tuned_validation_metrics": tuned_rf_validation_metrics,
            "validation_rmse_improvement_vs_untuned_percent": float(rf_improvement),
            "random_state": RANDOM_STATE,
            "scaling_applied": False,
        },
        "xgboost": {
            "candidate_count": len(xgb_candidate_results),
            "untuned_validation_metrics": untuned_xgb,
            "best_parameters": xgb_best_cv["parameters"],
            "best_mean_cv_rmse": xgb_best_cv["mean_cv_rmse"],
            "best_cv_rmse_std": xgb_best_cv["std_cv_rmse"],
            "tuned_validation_metrics": tuned_xgb_validation_metrics,
            "validation_rmse_improvement_vs_untuned_percent": float(xgb_improvement),
            "random_state": RANDOM_STATE,
            "base_parameters": XGBOOST_BASE_PARAMETERS,
            "scaling_applied": False,
        },
        "persistence_validation_metrics": validation_comparison["Persistence Baseline"],
        "linear_regression_validation_metrics": validation_comparison["Linear Regression"],
        "validation_model_comparison": validation_comparison,
        "best_validation_model_before_tuning": best_before_tuning,
        "current_best_validation_model_by_rmse": current_best_model,
        "best_validation_model_changed_after_tuning": current_best_model != best_before_tuning,
        "test_set_accessed": False,
        "note": "Test set was not loaded or evaluated in Phase 10; no final model selected.",
    }

    for output_path, payload in (
        (cv_results_path, cv_results),
        (summary_results_path, summary),
    ):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
            json.dump(payload, output_file, indent=2, sort_keys=True, allow_nan=False)
            output_file.write("\n")

    for phase_name, path in previous_paths.items():
        if _sha256_file(path) != previous_checksums[phase_name]:
            raise RuntimeError(f"{phase_name} validation results changed during tuning")

    artifacts: dict[str, object] = {
        "rf_cv_candidates": rf_candidates,
        "xgb_cv_candidates": xgb_candidate_results,
        "rf_best_cv": rf_best_cv,
        "xgb_best_cv": xgb_best_cv,
        "rf_validation_predictions": pd.Series(rf_validation_predictions),
        "xgb_validation_predictions": pd.Series(xgb_validation_predictions),
        "validation_actual": y_validation.reset_index(drop=True),
        "validation_dates": validation[DATE_COLUMN].reset_index(drop=True),
        "summary": summary,
    }
    return {"cv_results": cv_results, "summary": summary}, artifacts


def main() -> None:
    results, _ = run_phase10()
    summary = results["summary"]
    print(f"Train rows: {summary['train_rows']}; validation rows: {summary['validation_rows']}")
    print(f"Features: {summary['feature_count']}; TimeSeriesSplit folds: {CV_SPLITS}")
    print(
        "Random Forest candidates: "
        f"{summary['random_forest']['candidate_count']}; "
        f"best CV RMSE={summary['random_forest']['best_mean_cv_rmse']:.6f} "
        f"(+/- {summary['random_forest']['best_cv_rmse_std']:.6f})"
    )
    print(f"  Best RF parameters: {summary['random_forest']['best_parameters']}")
    print(
        "  Tuned RF validation: "
        f"{summary['random_forest']['tuned_validation_metrics']}"
    )
    print(
        "  Validation RMSE improvement vs untuned: "
        f"{summary['random_forest']['validation_rmse_improvement_vs_untuned_percent']:.6f}%"
    )
    print(
        "XGBoost candidates: "
        f"{summary['xgboost']['candidate_count']}; "
        f"best CV RMSE={summary['xgboost']['best_mean_cv_rmse']:.6f} "
        f"(+/- {summary['xgboost']['best_cv_rmse_std']:.6f})"
    )
    print(f"  Best XGBoost parameters: {summary['xgboost']['best_parameters']}")
    print(
        "  Tuned XGBoost validation: "
        f"{summary['xgboost']['tuned_validation_metrics']}"
    )
    print(
        "  Validation RMSE improvement vs untuned: "
        f"{summary['xgboost']['validation_rmse_improvement_vs_untuned_percent']:.6f}%"
    )
    print(f"Current best validation model by RMSE: {summary['current_best_validation_model_by_rmse']}")
    print("Test set was not loaded or evaluated in Phase 10.")
    print(f"CV candidate audit: {CV_RESULTS_PATH}")
    print(f"Tuning summary: {SUMMARY_RESULTS_PATH}")


if __name__ == "__main__":
    main()