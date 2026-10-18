"""Create reproducible chronological train, validation, and test datasets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURE_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "energydata_features.csv"
PROCESSED_DATA_DIRECTORY = PROJECT_ROOT / "data" / "processed"
RESULTS_DIRECTORY = PROJECT_ROOT / "ml" / "results"
TARGET_COLUMN = "target_appliances_next"
DATE_COLUMN = "date"
FORECAST_HORIZON_MINUTES = 10
EXPECTED_INTERVAL = pd.Timedelta(minutes=FORECAST_HORIZON_MINUTES)
TRAIN_FRACTION = 0.70
VALIDATION_FRACTION = 0.15
TEST_FRACTION = 0.15
SPLIT_FILENAMES = {
    "train": "energy_train.csv",
    "validation": "energy_validation.csv",
    "test": "energy_test.csv",
}


def sha256_file(path: Path) -> str:
    """Return a file's SHA-256 checksum using bounded memory."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(value, file, indent=2, sort_keys=True)
        file.write("\n")


def split_dataset(
    feature_data_path: Path = FEATURE_DATA_PATH,
    output_directory: Path = PROCESSED_DATA_DIRECTORY,
    results_directory: Path = RESULTS_DIRECTORY,
) -> tuple[dict[str, pd.DataFrame], dict[str, object]]:
    """Validate the feature data, split chronologically, and write artifacts."""
    feature_data_path = Path(feature_data_path).resolve()
    output_directory = Path(output_directory).resolve()
    results_directory = Path(results_directory).resolve()
    raw_directory = (PROJECT_ROOT / "data" / "raw").resolve()

    if not feature_data_path.is_file():
        raise FileNotFoundError(f"Feature dataset not found: {feature_data_path}")
    if raw_directory in output_directory.parents or output_directory == raw_directory:
        raise ValueError("Split files must not be written inside data/raw")
    if feature_data_path in (output_directory / name for name in SPLIT_FILENAMES.values()):
        raise ValueError("Split outputs must not overwrite the feature dataset")

    source_checksum_before = sha256_file(feature_data_path)
    source = pd.read_csv(feature_data_path)
    missing_required = sorted({DATE_COLUMN, TARGET_COLUMN}.difference(source.columns))
    if missing_required:
        raise ValueError(f"Feature dataset is missing required columns: {missing_required}")
    source[DATE_COLUMN] = pd.to_datetime(source[DATE_COLUMN], errors="raise")

    missing_values = int(source.isna().sum().sum())
    duplicate_rows = int(source.duplicated().sum())
    duplicate_timestamps = int(source[DATE_COLUMN].duplicated().sum())
    chronological = bool(source[DATE_COLUMN].is_monotonic_increasing)
    intervals = source[DATE_COLUMN].diff().dropna()
    exact_interval = bool(intervals.eq(EXPECTED_INTERVAL).all())
    if source.empty:
        raise ValueError("Feature dataset contains no rows")
    if missing_values:
        raise ValueError(f"Feature dataset contains {missing_values} missing values")
    if duplicate_rows:
        raise ValueError(f"Feature dataset contains {duplicate_rows} duplicate rows")
    if duplicate_timestamps:
        raise ValueError(f"Feature dataset contains {duplicate_timestamps} duplicate timestamps")
    if not chronological:
        raise ValueError("Feature dataset is not chronologically ordered")
    if not exact_interval:
        raise ValueError("Feature dataset does not have an exact 10-minute interval")
    if not pd.api.types.is_numeric_dtype(source[TARGET_COLUMN]):
        raise TypeError(f"{TARGET_COLUMN} must be numeric")

    model_feature_columns = [
        column for column in source.columns if column not in {DATE_COLUMN, TARGET_COLUMN}
    ]
    if not model_feature_columns:
        raise ValueError("No model input columns remain after excluding date and target")
    non_numeric_features = [
        column
        for column in model_feature_columns
        if not pd.api.types.is_numeric_dtype(source[column])
    ]
    if non_numeric_features:
        raise TypeError(f"Model input features must be numeric: {non_numeric_features}")
    if DATE_COLUMN in model_feature_columns or TARGET_COLUMN in model_feature_columns:
        raise AssertionError("Date or target leaked into the model feature schema")

    row_count = len(source)
    train_end = int(TRAIN_FRACTION * row_count)
    validation_end = int((TRAIN_FRACTION + VALIDATION_FRACTION) * row_count)
    if not 0 < train_end < validation_end < row_count:
        raise ValueError(f"Dataset is too small for the requested split: {row_count} rows")

    partitions = {
        "train": source.iloc[:train_end].copy().reset_index(drop=True),
        "validation": source.iloc[train_end:validation_end].copy().reset_index(drop=True),
        "test": source.iloc[validation_end:].copy().reset_index(drop=True),
    }

    for name, partition in partitions.items():
        if partition.empty:
            raise AssertionError(f"{name} split is empty")
        if not partition[DATE_COLUMN].is_monotonic_increasing:
            raise AssertionError(f"{name} split is not chronological")
        if partition[DATE_COLUMN].duplicated().any():
            raise AssertionError(f"{name} split contains duplicate timestamps")
        if partition.isna().sum().sum():
            raise AssertionError(f"{name} split contains missing values")
        if TARGET_COLUMN not in partition or DATE_COLUMN not in partition:
            raise AssertionError(f"{name} split is missing target or traceability date")

    train, validation, test = (
        partitions["train"],
        partitions["validation"],
        partitions["test"],
    )
    boundary_checks = {
        "train_before_validation": bool(
            train[DATE_COLUMN].max() < validation[DATE_COLUMN].min()
        ),
        "validation_before_test": bool(
            validation[DATE_COLUMN].max() < test[DATE_COLUMN].min()
        ),
        "train_validation_timestamps_disjoint": set(train[DATE_COLUMN]).isdisjoint(
            validation[DATE_COLUMN]
        ),
        "train_test_timestamps_disjoint": set(train[DATE_COLUMN]).isdisjoint(
            test[DATE_COLUMN]
        ),
        "validation_test_timestamps_disjoint": set(validation[DATE_COLUMN]).isdisjoint(
            test[DATE_COLUMN]
        ),
    }
    if not all(boundary_checks.values()):
        failed = [name for name, passed in boundary_checks.items() if not passed]
        raise AssertionError(f"Chronological split boundary checks failed: {failed}")

    combined = pd.concat(partitions.values(), ignore_index=True)
    if len(combined) != row_count:
        raise AssertionError("Split row counts do not add up to the source row count")
    if combined[DATE_COLUMN].duplicated().any():
        raise AssertionError("A source timestamp is duplicated across splits")
    if not combined[DATE_COLUMN].reset_index(drop=True).equals(
        source[DATE_COLUMN].reset_index(drop=True)
    ):
        raise AssertionError("Split concatenation lost, duplicated, or reordered source rows")
    assert_frame_equal(combined, source.reset_index(drop=True), check_dtype=False, check_exact=True)

    output_directory.mkdir(parents=True, exist_ok=True)
    split_checksums: dict[str, str] = {}
    split_paths: dict[str, Path] = {}
    for name, partition in partitions.items():
        path = output_directory / SPLIT_FILENAMES[name]
        partition.to_csv(
            path,
            index=False,
            date_format="%Y-%m-%dT%H:%M:%S",
            float_format="%.17g",
        )
        reloaded = pd.read_csv(path, parse_dates=[DATE_COLUMN], float_precision="round_trip")
        assert_frame_equal(partition, reloaded, check_dtype=False, check_exact=True)
        if reloaded.isna().sum().sum() or reloaded.duplicated().any():
            raise AssertionError(f"Reloaded {name} split failed integrity checks")
        if reloaded[DATE_COLUMN].duplicated().any():
            raise AssertionError(f"Reloaded {name} split contains duplicate dates")
        split_checksums[name] = sha256_file(path)
        split_paths[name] = path

    source_checksum_after = sha256_file(feature_data_path)
    if source_checksum_after != source_checksum_before:
        raise RuntimeError("Source feature dataset changed during split generation")

    split_rows = {name: len(frame) for name, frame in partitions.items()}
    split_percentages = {
        name: round(count / row_count * 100, 6) for name, count in split_rows.items()
    }
    split_boundaries = {
        "train_start": train[DATE_COLUMN].min().isoformat(sep=" "),
        "train_end": train[DATE_COLUMN].max().isoformat(sep=" "),
        "validation_start": validation[DATE_COLUMN].min().isoformat(sep=" "),
        "validation_end": validation[DATE_COLUMN].max().isoformat(sep=" "),
        "test_start": test[DATE_COLUMN].min().isoformat(sep=" "),
        "test_end": test[DATE_COLUMN].max().isoformat(sep=" "),
    }

    feature_schema = {
        "target_column": TARGET_COLUMN,
        "date_column": DATE_COLUMN,
        "model_feature_columns": model_feature_columns,
        "number_of_model_features": len(model_feature_columns),
        "forecast_horizon_minutes": FORECAST_HORIZON_MINUTES,
        "train_fraction": TRAIN_FRACTION,
        "validation_fraction": VALIDATION_FRACTION,
        "test_fraction": TEST_FRACTION,
    }
    split_metadata = {
        "total_supervised_rows": row_count,
        "train_rows": split_rows["train"],
        "validation_rows": split_rows["validation"],
        "test_rows": split_rows["test"],
        "train_percentage": split_percentages["train"],
        "validation_percentage": split_percentages["validation"],
        "test_percentage": split_percentages["test"],
        **split_boundaries,
        "target_column": TARGET_COLUMN,
        "forecast_horizon_minutes": FORECAST_HORIZON_MINUTES,
        "source_feature_dataset_sha256": source_checksum_before,
        "split_csv_sha256": split_checksums,
        "split_method": "contiguous chronological partitions; no shuffle",
        "boundary_checks": boundary_checks,
    }
    _write_json(results_directory / "feature_schema.json", feature_schema)
    _write_json(results_directory / "split_metadata.json", split_metadata)

    return partitions, {
        "source_path": feature_data_path,
        "source_checksum_before": source_checksum_before,
        "source_checksum_after": source_checksum_after,
        "total_rows": row_count,
        "split_rows": split_rows,
        "split_percentages": split_percentages,
        "boundaries": split_boundaries,
        "boundary_checks": boundary_checks,
        "model_feature_columns": model_feature_columns,
        "number_of_model_features": len(model_feature_columns),
        "split_paths": split_paths,
        "split_checksums": split_checksums,
        "feature_schema_path": results_directory / "feature_schema.json",
        "split_metadata_path": results_directory / "split_metadata.json",
        "target_column": TARGET_COLUMN,
        "forecast_horizon_minutes": FORECAST_HORIZON_MINUTES,
    }


def main() -> None:
    partitions, report = split_dataset()
    print(f"Feature dataset: {report['source_path']}")
    print(f"Source SHA-256: {report['source_checksum_before']}")
    print(f"Source SHA-256 after split: {report['source_checksum_after']}")
    print(f"Total rows: {report['total_rows']}")
    print(f"Model feature count: {report['number_of_model_features']}")
    print(f"Target: {report['target_column']}; horizon: {report['forecast_horizon_minutes']} minutes")
    for name, frame in partitions.items():
        start = frame[DATE_COLUMN].min().isoformat(sep=" ")
        end = frame[DATE_COLUMN].max().isoformat(sep=" ")
        print(
            f"{name.title()}: {report['split_rows'][name]} rows "
            f"({report['split_percentages'][name]}%); {start} through {end}"
        )
        print(f"  CSV: {report['split_paths'][name]}")
        print(f"  SHA-256: {report['split_checksums'][name]}")
        print("  Target distribution (diagnostic only):")
        print(frame[TARGET_COLUMN].agg(["mean", "median", "std", "min", "max"]).to_string())
    print("Boundary and overlap checks:")
    for name, passed in report["boundary_checks"].items():
        print(f"  {name}: {passed}")
    print(f"Feature schema: {report['feature_schema_path']}")
    print(f"Split metadata: {report['split_metadata_path']}")
    print("No models trained; no scaling or fitting performed.")


if __name__ == "__main__":
    main()