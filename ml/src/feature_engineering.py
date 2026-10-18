"""Build a leakage-checked one-step-ahead energy forecasting dataset."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "energydata_cleaned.csv"
OUTPUT_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "energydata_features.csv"
TARGET_COLUMN = "Appliances"
NEXT_TARGET_COLUMN = "target_appliances_next"
EXPECTED_INTERVAL = pd.Timedelta(minutes=10)
TEMPORAL_FEATURES = ("hour", "day_of_week", "month", "is_weekend")
CYCLICAL_FEATURES = ("hour_sin", "hour_cos", "dow_sin", "dow_cos")
LAG_STEPS = (1, 6, 144, 1008)
LAG_FEATURES = tuple(f"appliances_lag_{steps}" for steps in LAG_STEPS)
ROLLING_WINDOWS = {"1h": 6, "24h": 144}
ROLLING_FEATURES = tuple(
    feature
    for period in ROLLING_WINDOWS
    for feature in (f"appliances_roll_mean_{period}", f"appliances_roll_std_{period}")
)
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def sha256_file(path: Path) -> str:
    """Return the SHA-256 checksum for a file, reading it in bounded chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_cleaned_input(frame: pd.DataFrame) -> dict[str, object]:
    required = {"date", TARGET_COLUMN}
    missing_columns = sorted(required.difference(frame.columns))
    if missing_columns:
        raise ValueError(f"Cleaned dataset is missing required columns: {missing_columns}")

    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    missing_values = int(frame.isna().sum().sum())
    duplicate_rows = int(frame.duplicated().sum())
    duplicate_timestamps = int(frame["date"].duplicated().sum())
    chronological = bool(frame["date"].is_monotonic_increasing)
    intervals = frame["date"].diff().dropna()
    exact_intervals = bool(intervals.eq(EXPECTED_INTERVAL).all())
    non_numeric = [
        column
        for column in frame.columns
        if column != "date" and not pd.api.types.is_numeric_dtype(frame[column])
    ]

    problems = []
    if frame.empty:
        problems.append("dataset contains no rows")
    if missing_values:
        problems.append(f"{missing_values} missing values detected")
    if duplicate_rows:
        problems.append(f"{duplicate_rows} duplicate rows detected")
    if duplicate_timestamps:
        problems.append(f"{duplicate_timestamps} duplicate timestamps detected")
    if not chronological:
        problems.append("timestamps are not chronologically ordered")
    if not exact_intervals:
        problems.append("timestamps do not have an exact 10-minute interval")
    if non_numeric:
        problems.append(f"non-numeric measurement columns detected: {non_numeric}")

    if problems:
        raise ValueError("Cleaned dataset failed integrity checks: " + "; ".join(problems))

    return {
        "rows": len(frame),
        "columns": len(frame.columns),
        "missing_values": missing_values,
        "duplicate_rows": duplicate_rows,
        "duplicate_timestamps": duplicate_timestamps,
        "chronologically_ordered": chronological,
        "interval_is_exact": exact_intervals,
    }


def _validate_alignment(
    source: pd.DataFrame,
    engineered: pd.DataFrame,
    valid_positions: np.ndarray,
    original_columns: list[str],
) -> dict[str, bool]:
    source_energy = source[TARGET_COLUMN]
    checks: dict[str, bool] = {}

    expected_target = source_energy.shift(-1).iloc[valid_positions].to_numpy()
    checks["next_target_equals_original_next_observation"] = np.array_equal(
        engineered[NEXT_TARGET_COLUMN].to_numpy(), expected_target
    )

    for steps, feature in zip(LAG_STEPS, LAG_FEATURES):
        expected_lag = source_energy.shift(steps).iloc[valid_positions].to_numpy()
        checks[f"{feature}_uses_history_only"] = np.array_equal(
            engineered[feature].to_numpy(), expected_lag
        )

    for period, window in ROLLING_WINDOWS.items():
        rolling = source_energy.rolling(window=window, min_periods=window, center=False)
        expected_mean = rolling.mean().iloc[valid_positions].to_numpy()
        expected_std = rolling.std(ddof=1).iloc[valid_positions].to_numpy()
        checks[f"rolling_{period}_is_backward_looking"] = (
            np.array_equal(
                engineered[f"appliances_roll_mean_{period}"].to_numpy(), expected_mean
            )
            and np.array_equal(
                engineered[f"appliances_roll_std_{period}"].to_numpy(), expected_std
            )
        )

    checks["target_is_not_an_input_feature"] = NEXT_TARGET_COLUMN not in original_columns + list(
        TEMPORAL_FEATURES + CYCLICAL_FEATURES + LAG_FEATURES + ROLLING_FEATURES
    )
    checks["date_is_not_a_numeric_model_input"] = "date" not in original_columns[1:]

    origin_dates = source["date"].iloc[valid_positions].reset_index(drop=True)
    target_dates = source["date"].shift(-1).iloc[valid_positions].reset_index(drop=True)
    checks["target_timestamp_is_exactly_10_minutes_after_origin"] = bool(
        target_dates.sub(origin_dates).eq(EXPECTED_INTERVAL).all()
    )

    physical_columns = [column for column in original_columns if column != "date"]
    checks["physical_inputs_are_values_at_origin"] = all(
        np.array_equal(
            engineered[column].to_numpy(),
            source[column].iloc[valid_positions].to_numpy(),
        )
        for column in physical_columns
    )

    origin_dates_for_features = source["date"].iloc[valid_positions]
    expected_hour = origin_dates_for_features.dt.hour.to_numpy()
    expected_day = origin_dates_for_features.dt.dayofweek.to_numpy()
    checks["temporal_features_match_origin_timestamp"] = (
        np.array_equal(engineered["hour"].to_numpy(), expected_hour)
        and np.array_equal(engineered["day_of_week"].to_numpy(), expected_day)
        and np.array_equal(
            engineered["month"].to_numpy(), origin_dates_for_features.dt.month.to_numpy()
        )
        and np.array_equal(
            engineered["is_weekend"].to_numpy(), (expected_day >= 5).astype("int8")
        )
    )
    checks["cyclical_features_match_origin_timestamp"] = (
        np.allclose(
            engineered["hour_sin"].to_numpy(), np.sin(2 * np.pi * expected_hour / 24)
        )
        and np.allclose(
            engineered["hour_cos"].to_numpy(), np.cos(2 * np.pi * expected_hour / 24)
        )
        and np.allclose(
            engineered["dow_sin"].to_numpy(), np.sin(2 * np.pi * expected_day / 7)
        )
        and np.allclose(
            engineered["dow_cos"].to_numpy(), np.cos(2 * np.pi * expected_day / 7)
        )
    )

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise AssertionError(f"Feature alignment/leakage checks failed: {failed}")
    return checks


def engineer_dataset(
    input_path: Path = INPUT_DATA_PATH,
    output_path: Path = OUTPUT_DATA_PATH,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Create origin-time features and a ten-minute-ahead Appliances target."""
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    raw_directory = (PROJECT_ROOT / "data" / "raw").resolve()

    if not input_path.is_file():
        raise FileNotFoundError(f"Cleaned dataset not found: {input_path}")
    if input_path == output_path:
        raise ValueError("Feature output path must not overwrite the cleaned input")
    if output_path == raw_directory or raw_directory in output_path.parents:
        raise ValueError("Feature output must not be written inside data/raw")

    input_checksum_before = sha256_file(input_path)
    source = pd.read_csv(input_path)
    input_validation = _validate_cleaned_input(source)
    source = source.reset_index(drop=True)
    original_columns = list(source.columns)
    original_rows = len(source)

    engineered = source.copy()
    engineered["hour"] = source["date"].dt.hour
    engineered["day_of_week"] = source["date"].dt.dayofweek
    engineered["month"] = source["date"].dt.month
    engineered["is_weekend"] = (source["date"].dt.dayofweek >= 5).astype("int8")

    engineered["hour_sin"] = np.sin(2 * np.pi * engineered["hour"] / 24)
    engineered["hour_cos"] = np.cos(2 * np.pi * engineered["hour"] / 24)
    engineered["dow_sin"] = np.sin(2 * np.pi * engineered["day_of_week"] / 7)
    engineered["dow_cos"] = np.cos(2 * np.pi * engineered["day_of_week"] / 7)

    for steps, feature in zip(LAG_STEPS, LAG_FEATURES):
        engineered[feature] = source[TARGET_COLUMN].shift(steps)

    for period, window in ROLLING_WINDOWS.items():
        # The uncentered full window ends at the current forecast origin t.
        rolling = source[TARGET_COLUMN].rolling(window=window, min_periods=window, center=False)
        engineered[f"appliances_roll_mean_{period}"] = rolling.mean()
        engineered[f"appliances_roll_std_{period}"] = rolling.std(ddof=1)

    # This is the only future shift: it creates the label, never an input feature.
    engineered[NEXT_TARGET_COLUMN] = source[TARGET_COLUMN].shift(-1)

    engineered_columns = list(
        TEMPORAL_FEATURES + CYCLICAL_FEATURES + LAG_FEATURES + ROLLING_FEATURES
    )
    expected_columns = original_columns + engineered_columns + [NEXT_TARGET_COLUMN]
    if list(engineered.columns) != expected_columns:
        raise AssertionError("Generated columns differ from the approved feature schema")

    input_feature_columns = [
        column for column in expected_columns if column not in {"date", NEXT_TARGET_COLUMN}
    ]
    if TARGET_COLUMN not in input_feature_columns:
        raise AssertionError("Current Appliances at time t must remain an input feature")

    required_sample_columns = input_feature_columns + [NEXT_TARGET_COLUMN]
    valid_mask = engineered[required_sample_columns].notna().all(axis=1)
    valid_positions = np.flatnonzero(valid_mask.to_numpy())
    if not len(valid_positions):
        raise ValueError("No supervised samples remain after temporal alignment")
    if not np.array_equal(
        valid_positions,
        np.arange(valid_positions[0], valid_positions[-1] + 1),
    ):
        raise ValueError("Unavailable temporal context is not limited to leading/trailing rows")

    rows_excluded_beginning = int(valid_positions[0])
    rows_excluded_end = int(original_rows - valid_positions[-1] - 1)
    if rows_excluded_beginning != max(LAG_STEPS) or rows_excluded_end != 1:
        raise ValueError(
            "Unexpected supervised row exclusions: "
            f"{rows_excluded_beginning} at start, {rows_excluded_end} at end"
        )

    output_columns = expected_columns
    supervised = engineered.loc[valid_mask, output_columns].copy()
    if supervised[required_sample_columns].isna().any().any():
        raise AssertionError("Unavailable features remain in the final supervised dataset")
    if not supervised["date"].is_monotonic_increasing:
        raise AssertionError("Feature dataset timestamps are not chronological")
    if supervised["date"].duplicated().any():
        raise AssertionError("Feature dataset contains duplicate timestamps")

    alignment_checks = _validate_alignment(
        source,
        supervised,
        valid_positions,
        original_columns,
    )
    supervised = supervised.reset_index(drop=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    supervised.to_csv(
        output_path,
        index=False,
        date_format=DATE_FORMAT,
        float_format="%.17g",
    )

    reloaded = pd.read_csv(
        output_path,
        parse_dates=["date"],
        float_precision="round_trip",
    )
    if reloaded.shape != supervised.shape:
        raise AssertionError("Reloaded feature CSV has an unexpected shape")
    if reloaded.columns.tolist() != output_columns:
        raise AssertionError("Reloaded feature CSV has an unexpected schema")
    if reloaded.isna().sum().sum():
        raise AssertionError("Reloaded feature CSV contains missing values")
    if reloaded.duplicated().any() or reloaded["date"].duplicated().any():
        raise AssertionError("Reloaded feature CSV contains duplicates")
    if not reloaded["date"].is_monotonic_increasing:
        raise AssertionError("Reloaded feature CSV is not chronological")
    assert_frame_equal(supervised, reloaded, check_dtype=False, check_exact=True)

    input_checksum_after = sha256_file(input_path)
    if input_checksum_after != input_checksum_before:
        raise RuntimeError("Cleaned input checksum changed during feature generation")

    return reloaded, {
        "input_path": input_path,
        "output_path": output_path,
        "input_checksum_before": input_checksum_before,
        "input_checksum_after": input_checksum_after,
        "output_checksum": sha256_file(output_path),
        "input_validation": input_validation,
        "input_shape": (original_rows, len(original_columns)),
        "output_shape": reloaded.shape,
        "rows_excluded_beginning": rows_excluded_beginning,
        "rows_excluded_end": rows_excluded_end,
        "rows_excluded_total": original_rows - len(reloaded),
        "temporal_features": list(TEMPORAL_FEATURES),
        "cyclical_features": list(CYCLICAL_FEATURES),
        "lag_features": list(LAG_FEATURES),
        "rolling_features": list(ROLLING_FEATURES),
        "input_feature_columns": input_feature_columns,
        "target_column": NEXT_TARGET_COLUMN,
        "forecast_horizon": EXPECTED_INTERVAL,
        "alignment_checks": alignment_checks,
        "missing_values": int(reloaded.isna().sum().sum()),
        "duplicate_rows": int(reloaded.duplicated().sum()),
        "duplicate_timestamps": int(reloaded["date"].duplicated().sum()),
        "chronologically_ordered": bool(reloaded["date"].is_monotonic_increasing),
        "dtypes": {column: str(dtype) for column, dtype in reloaded.dtypes.items()},
    }


def main() -> None:
    features, report = engineer_dataset()
    print(f"Cleaned input: {report['input_path']}")
    print(f"Input shape: {report['input_shape']}")
    print(f"Input SHA-256 before: {report['input_checksum_before']}")
    print(f"Input SHA-256 after:  {report['input_checksum_after']}")
    print(f"Feature dataset: {report['output_path']}")
    print(f"Feature shape: {report['output_shape']}")
    print(f"Rows excluded at start: {report['rows_excluded_beginning']} (7-day historical lag context)")
    print(f"Rows excluded at end: {report['rows_excluded_end']} (next-step target unavailable)")
    print(f"Rows excluded total: {report['rows_excluded_total']}")
    print(f"Target: {report['target_column']} ({report['forecast_horizon']} ahead)")
    print(f"Feature columns: {', '.join(report['input_feature_columns'])}")
    print(f"Feature SHA-256: {report['output_checksum']}")
    print(f"Missing values: {report['missing_values']}")
    print(f"Duplicate rows: {report['duplicate_rows']}")
    print(f"Duplicate timestamps: {report['duplicate_timestamps']}")
    print(f"Chronologically ordered: {report['chronologically_ordered']}")
    print("Leakage/alignment checks:")
    for name, passed in report["alignment_checks"].items():
        print(f"  {name}: {passed}")
    print("Feature data types:")
    for column, dtype in report["dtypes"].items():
        print(f"  {column}: {dtype}")


if __name__ == "__main__":
    main()