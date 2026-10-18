"""Post-hoc gain and TEST permutation importance for the locked Phase 11 model.

Run normally, then with --verify-reproducibility. No model is persisted;
Phase 11 artifacts are read-only. TEST perturbations are interpretation only.
"""
from __future__ import annotations

import argparse
from importlib.metadata import version
import platform

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

if __package__:
    from .evaluate_final_model import ROOT, RESULTS, GENERATED, load_split, read_json, sha256, write_new
else:
    from evaluate_final_model import ROOT, RESULTS, GENERATED, load_split, read_json, sha256, write_new

RESULT_PATH = RESULTS / "phase12_feature_importance.json"
REPLAY_PATH = RESULTS / "phase12_reproducibility.json"
REPEATS = 10
SEED = 42
METRIC_RTOL = 1e-9
METRIC_ATOL = 1e-9
LOW_IMPORTANCE_WH = 0.1  # Predeclared description only; never a selection rule.
TEMPORAL = ("hour", "day_of_week", "month", "is_weekend", "hour_sin", "hour_cos", "dow_sin", "dow_cos")
INDOOR_INDICES = (1, 2, 3, 4, 5, 7, 8, 9)
WEATHER = ("T6", "RH_6", "T_out", "Press_mm_hg", "RH_out", "Windspeed", "Visibility", "Tdewpoint")


def feature_groups(features):
    """Use data/raw/README.md groups plus Phase 5 history/temporal features."""
    groups = {}
    for name in features:
        if name == "Appliances" or name.startswith(("appliances_lag_", "appliances_roll_")):
            group = "Historical/current consumption"
        elif name in TEMPORAL:
            group = "Temporal"
        elif name == "lights":
            group = "Lighting"
        elif name in {f"T{i}" for i in INDOOR_INDICES}:
            group = "Indoor temperature"
        elif name in {f"RH_{i}" for i in INDOOR_INDICES}:
            group = "Indoor humidity"
        elif name in WEATHER:
            group = "Outdoor/weather"
        else:
            raise ValueError(f"Feature has no documented group: {name}")
        groups[name] = group
    return groups


def gain_values(booster, features):
    """Map named or positional booster keys; unused features receive zero."""
    if booster.feature_names is not None and booster.feature_names != features:
        raise ValueError("Booster feature order differs from locked schema")
    scores = booster.get_score(importance_type="gain")
    mapped = dict.fromkeys(features, 0.0)
    for key, value in scores.items():
        if key in mapped:
            name = key
        elif booster.feature_names is None and key.startswith("f") and key[1:].isdigit() and int(key[1:]) < len(features):
            name = features[int(key[1:])]
        else:
            raise ValueError(f"Unknown booster feature key: {key}")
        mapped[name] = float(value)
    values = np.array([mapped[name] for name in features])
    if not np.isfinite(values).all() or (values < 0).any() or values.sum() <= 0:
        raise ValueError("Invalid gain importance")
    return values


def verify_metrics(actual, predictions, phase11):
    """Fail before ANY importance computation if reconstruction differs."""
    metrics = {"mae": float(mean_absolute_error(actual, predictions)),
               "rmse": float(np.sqrt(mean_squared_error(actual, predictions))),
               "r2": float(r2_score(actual, predictions))}
    expected = {name: phase11[f"test_{name}"] for name in metrics}
    matches = {name: bool(np.isclose(value, expected[name], rtol=METRIC_RTOL, atol=METRIC_ATOL)) for name, value in metrics.items()}
    if not all(matches.values()):
        raise ValueError(f"STOP: reconstructed model does not reproduce Phase 11: actual={metrics}; expected={expected}")
    return {"passed": True, "expected": expected, "reconstructed": metrics,
            "absolute_differences": {k: abs(metrics[k] - expected[k]) for k in metrics},
            "rtol": METRIC_RTOL, "atol": METRIC_ATOL,
            "purpose": "Equivalence check only; Phase 11 remains the final held-out evaluation"}


def reconstruct_final_model():
    phase11_path = RESULTS / "phase11_final_test_evaluation.json"
    lock_path = RESULTS / "phase11_selection_lock.json"
    replay_path = RESULTS / "phase11_reproducibility.json"
    phase11, lock = read_json(phase11_path), read_json(lock_path)
    summary = read_json(RESULTS / "phase10_tuning_summary.json")
    schema = read_json(RESULTS / "feature_schema.json")
    metadata = read_json(RESULTS / "split_metadata.json")
    if sha256(lock_path) != phase11["selection_lock_sha256"]:
        raise ValueError("Phase 11 lock checksum mismatch")
    if read_json(replay_path)["original_result_sha256"] != sha256(phase11_path):
        raise ValueError("Phase 11 original result checksum mismatch")
    params = lock["selected_hyperparameters"]
    expected_params = {**summary["xgboost"]["base_parameters"], **summary["xgboost"]["best_parameters"]}
    if (lock["final_model_name"] != "Tuned XGBoost" or phase11["final_model_name"] != lock["final_model_name"]
        or params != expected_params or phase11["selected_hyperparameters"] != params):
        raise ValueError("Locked model/configuration differs from Phase 10/11")
    features, target = schema["model_feature_columns"], schema["target_column"]
    if (features != lock["feature_columns"] or features != phase11["feature_columns"]
        or len(features) != 42 or len(set(features)) != 42 or schema["number_of_model_features"] != 42
        or "date" in features or target in features or "Appliances" not in features
        or target != phase11["target"] or schema["forecast_horizon_minutes"] != phase11["forecast_horizon_minutes"]):
        raise ValueError("Approved feature/target/horizon schema changed")
    dependencies = {p: version(p) for p in lock["dependencies"]}
    if dependencies != lock["dependencies"] or platform.python_version() != lock["python_version"]:
        raise ValueError("Reconstruction requires recorded Phase 11 environment")
    checksums = dict(phase11["input_sha256"])
    checksums.update({p.relative_to(ROOT).as_posix(): sha256(p) for p in (phase11_path, lock_path, replay_path)})
    for relative, expected in checksums.items():
        if sha256(ROOT / relative) != expected:
            raise ValueError(f"Phase 11 input changed: {relative}")
    train, _ = load_split("train", schema, metadata)
    validation, _ = load_split("validation", schema, metadata)
    if not train.date.iloc[-1] < validation.date.iloc[0]:
        raise ValueError("Development chronology invalid")
    development = pd.concat([train, validation], ignore_index=True)
    if (len(development) != phase11["development_rows"] or len(development) != len(train) + len(validation)
        or development.date.duplicated().any() or development.isna().any().any()
        or not development.date.is_monotonic_increasing):
        raise ValueError("Development dataset differs from Phase 11")
    model = XGBRegressor(**params)
    model.fit(development.loc[:, features], development[target])
    test, _ = load_split("test", schema, metadata)
    if not development.date.iloc[-1] < test.date.iloc[0] or len(test) != phase11["test_rows"]:
        raise ValueError("TEST boundary or row count differs from Phase 11")
    X_test, y_test = test.loc[:, features], test[target]
    reproduction = verify_metrics(y_test, model.predict(X_test), phase11)
    return model, X_test, y_test, reproduction, checksums, lock, dependencies


def summarize(table):
    gain = table.sort_values("gain_rank")
    perm = table.sort_values("permutation_rank")
    gain10, perm10 = gain.head(10).feature.tolist(), perm.head(10).feature.tolist()
    groups = table.groupby("group", sort=True).normalized_gain.sum().sort_values(ascending=False)
    categories = {
        "historical_current_consumption": table.group.eq("Historical/current consumption"),
        "temporal": table.group.eq("Temporal"),
        "temperature_all_locations": table.feature.isin([f"T{i}" for i in range(1, 10)] + ["T_out", "Tdewpoint"]),
        "indoor_temperature": table.group.eq("Indoor temperature"),
        "humidity_all_locations": table.feature.str.startswith("RH_"),
        "indoor_humidity": table.group.eq("Indoor humidity"),
        "outdoor_weather": table.group.eq("Outdoor/weather"),
        "lighting": table.group.eq("Lighting"),
    }
    category_rankings = {name: {"by_gain": table.loc[mask].sort_values("gain_rank").to_dict(orient="records"),
                                "by_permutation": table.loc[mask].sort_values("permutation_rank").to_dict(orient="records")}
                         for name, mask in categories.items()}
    return {
        "top_10_gain_features": gain.head(10).to_dict(orient="records"),
        "top_15_gain_features": gain.head(15).to_dict(orient="records"),
        "top_10_permutation_features": perm.head(10).to_dict(orient="records"),
        "top_15_permutation_features": perm.head(15).to_dict(orient="records"),
        "top_10_overlap": [n for n in gain10 if n in perm10],
        "top_10_gain_only": [n for n in gain10 if n not in perm10],
        "top_10_permutation_only": [n for n in perm10 if n not in gain10],
        "very_low_absolute_permutation_threshold_wh": LOW_IMPORTANCE_WH,
        "very_low_absolute_permutation_features": table.loc[table.permutation_mean.abs() <= LOW_IMPORTANCE_WH, "feature"].tolist(),
        "negative_permutation_features": table.loc[table.permutation_mean < 0, "feature"].tolist(),
        "group_normalized_gain_totals": {k: float(v) for k, v in groups.items()},
        "category_rankings": category_rankings,
        "historical_features_in_gain_top10": sum(n in gain10 for n in table.loc[categories["historical_current_consumption"], "feature"]),
        "historical_features_in_permutation_top10": sum(n in perm10 for n in table.loc[categories["historical_current_consumption"], "feature"]),
    }


def calculate_importance():
    model, X_test, y_test, reproduction, checksums, lock, dependencies = reconstruct_final_model()
    # Importance occurs ONLY after the Phase 11 metric-equivalence gate passes.
    features = X_test.columns.tolist()
    gains = gain_values(model.get_booster(), features)
    permutation = permutation_importance(model, X_test, y_test,
        scoring="neg_root_mean_squared_error", n_repeats=REPEATS,
        random_state=SEED, n_jobs=1, max_samples=1.0)
    if permutation.importances.shape != (42, REPEATS) or not np.isfinite(permutation.importances).all():
        raise ValueError("Invalid permutation importance shape/values")
    groups = feature_groups(features)
    table = pd.DataFrame({"feature": features, "group": [groups[f] for f in features],
        "gain": gains, "normalized_gain": gains / gains.sum(),
        "permutation_mean": permutation.importances_mean,
        "permutation_std": permutation.importances_std,
        "permutation_repetitions": permutation.importances.tolist()})
    for value, rank in (("gain", "gain_rank"), ("permutation_mean", "permutation_rank")):
        ordered = table.sort_values([value, "feature"], ascending=[False, True]).index
        table.loc[ordered, rank] = np.arange(1, len(table) + 1)
        table[rank] = table[rank].astype(int)
    report = {
        "final_model_name": lock["final_model_name"], "selected_hyperparameters": lock["selected_hyperparameters"],
        "feature_count": len(features), "feature_columns": features,
        "target": y_test.name, "forecast_horizon_minutes": 10,
        "development_rows": read_json(RESULTS / "phase11_final_test_evaluation.json")["development_rows"],
        "explanation_rows": len(X_test), "explanation_dataset": "Full held-out TEST; post-hoc interpretation only",
        "gain_dataset": "TRAIN + VALIDATION fitted booster split statistics",
        "permutation_repeats": REPEATS, "random_state": SEED, "n_jobs": 1,
        "permutation_scoring": "neg_root_mean_squared_error", "permutation_max_samples": 1.0,
        "permutation_interpretation": "Importance = permuted RMSE minus unpermuted RMSE (Wh); positive means worse errors after shuffling; negative means improved errors. Values are not clipped.",
        "permutation_std_definition": "Population std (ddof=0) across 10 permutations; not a confidence interval or sampling uncertainty",
        "gain_definition": "Average training objective gain across splits using each feature; missing split scores assigned zero",
        "normalized_gain_definition": "Each feature average gain divided by sum of all feature average gains",
        "group_summary_interpretation": "Sum of normalized per-feature average gains within each documented group; descriptive, not total split gain, energy shares or causal contributions. Permutation values are not summed.",
        "ranking_ties": "Descending score then alphabetical feature name; tied ranks have no substantive ordering",
        "phase11_metric_reproduction": reproduction,
        "features": table.sort_values("gain_rank").to_dict(orient="records"),
        **summarize(table), "dependencies": dependencies,
        "input_sha256": checksums, "input_checksums_unchanged": True,
        "model_changed": False, "feature_selection_performed": False,
        "tuning_performed": False, "alternative_models_evaluated": False,
        "test_influenced_model_development": False, "model_artifact_saved": False,
        "test_usage_statement": "Phase 11 final evaluation remains unchanged. Phase 12 reuses TEST only for equivalence verification and post-hoc interpretation; no development decisions follow.",
        "limitations": [
            "Predictive importance is model/period specific; it does not establish causality or intervention savings.",
            "Correlated history, temporal and environmental inputs can substitute and distribute or mask importance.",
            "Independent row permutations break serial dependence and cross-feature consistency, creating possibly implausible inputs. This is a perturbation diagnostic, not an operational forecast or causal intervention.",
            "Repeat standard deviations describe permutation variability only, not statistical confidence.",
            "Single-building January-May collection, with partial January and May; no full-year seasonal generalization.",
            "Phase 3 marginal correlations concern contemporaneous Appliances; the model predicts next-step Appliances conditionally on all features, so these measures are not directly interchangeable.",
            "lights is measured lighting energy, not an occupancy sensor.",
        ],
        "method_sources": ["https://xgboost.readthedocs.io/en/stable/python/python_api.html#xgboost.Booster.get_score",
                           "https://scikit-learn.org/stable/modules/permutation_importance.html"],
    }
    if any(sha256(ROOT / path) != expected for path, expected in checksums.items()):
        raise RuntimeError("A Phase 11 input/artifact changed during explainability")
    return report, table.drop(columns="permutation_repetitions")


def load_saved_explanation():
    """Notebook loader: no model fitting or repeated TEST interpretation."""
    report = read_json(RESULT_PATH)
    return report, pd.DataFrame(report["features"]).drop(columns="permutation_repetitions")


def run_phase12(verify_reproducibility=False):
    if RESULT_PATH.exists() and not verify_reproducibility:
        raise FileExistsError("Explanation exists; use notebook loader or --verify-reproducibility")
    if verify_reproducibility and not RESULT_PATH.exists():
        raise FileNotFoundError("Original Phase 12 explanation required for replay")
    report, table = calculate_importance()
    if verify_reproducibility:
        original = read_json(RESULT_PATH)
        if report != original:
            raise AssertionError("Explainability replay differs; original result preserved")
        replay = {"phase11_metrics_reproduced": True, "gain_reproduced_exactly": True,
            "permutation_means_stds_and_all_repetitions_reproduced_exactly": True,
            "whole_result_reproduced_exactly": True, "original_result_sha256": sha256(RESULT_PATH),
            "comparison": "Exact JSON numeric equality; no tolerance was needed"}
        if REPLAY_PATH.exists():
            if replay != read_json(REPLAY_PATH):
                raise AssertionError("Reproducibility record mismatch")
        else:
            write_new(REPLAY_PATH, replay)
    else:
        GENERATED.mkdir(parents=True, exist_ok=True)
        table.sort_values("gain_rank").to_csv(GENERATED / "phase12_feature_importance.csv", index=False)
        write_new(RESULT_PATH, report)
    return report, table


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-reproducibility", action="store_true")
    args = parser.parse_args()
    report, _ = run_phase12(args.verify_reproducibility)
    print("Final model:", report["final_model_name"], "| features:", report["feature_count"])
    print("Phase 11 metric reproduction:", report["phase11_metric_reproduction"])
    for label, key in (("Gain", "top_10_gain_features"), ("Permutation", "top_10_permutation_features")):
        print(label, "top 10:")
        for row in report[key]:
            print(f"  {row['feature']}: gain={row['normalized_gain']:.9f}; permutation={row['permutation_mean']:.9f} +/- {row['permutation_std']:.9f} Wh")
    print("Post-hoc only. No model, feature or development decisions changed.")


if __name__ == "__main__":
    main()
