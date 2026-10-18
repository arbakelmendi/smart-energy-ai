"""Reproducibly validate and export the Phase 4 processed energy dataset."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "energydata_complete.csv"
PROCESSED_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "energydata_cleaned.csv"
REQUIRED_COLUMNS = {"date", "Appliances", "rv1", "rv2"}
COLUMNS_TO_REMOVE = ("rv1", "rv2")
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def sha256_file(path: Path) -> str:
    """Return the SHA-256 checksum for a file, reading it in bounded chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_frame(frame: pd.DataFrame, label: str) -> dict[str, object]:
    missing_by_column = frame.isna().sum()
    missing_total = int(missing_by_column.sum())
    duplicate_rows = int(frame.duplicated().sum())
    duplicate_timestamps = int(frame["date"].duplicated().sum())
    chronological = bool(frame["date"].is_monotonic_increasing)

    problems = []
    if missing_total:
        details = {name: int(count) for name, count in missing_by_column.items() if count}
        problems.append(f"missing values detected: {details}")
    if duplicate_rows:
        problems.append(f"{duplicate_rows} duplicate rows detected")
    if duplicate_timestamps:
        problems.append(f"{duplicate_timestamps} duplicate timestamps detected")
    if not chronological:
        problems.append("timestamps are not chronologically ordered")

    non_numeric = [
        column
        for column in frame.columns
        if column != "date" and not pd.api.types.is_numeric_dtype(frame[column])
    ]
    if non_numeric:
        problems.append(f"non-numeric measurement columns detected: {non_numeric}")
    if not pd.api.types.is_numeric_dtype(frame["Appliances"]):
        problems.append("Appliances target is not numeric")

    if problems:
        raise ValueError(f"{label} failed data-integrity checks: " + "; ".join(problems))

    return {
        "rows": len(frame),
        "columns": len(frame.columns),
        "missing_values": missing_total,
        "duplicate_rows": duplicate_rows,
        "duplicate_timestamps": duplicate_timestamps,
        "chronologically_ordered": chronological,
        "dtypes": {column: str(dtype) for column, dtype in frame.dtypes.items()},
    }


def preprocess_dataset(
    input_path: Path = RAW_DATA_PATH,
    output_path: Path = PROCESSED_DATA_PATH,
) -> dict[str, object]:
    """Validate raw data, remove only rv1/rv2, and write the processed CSV."""
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    raw_directory = (PROJECT_ROOT / "data" / "raw").resolve()

    if not input_path.is_file():
        raise FileNotFoundError(f"Raw dataset not found: {input_path}")
    if input_path == output_path:
        raise ValueError("Processed output path must never overwrite the raw dataset")
    if output_path == raw_directory or raw_directory in output_path.parents:
        raise ValueError("Processed output must not be written inside data/raw")

    raw_checksum_before = sha256_file(input_path)
    frame = pd.read_csv(input_path)
    missing_required = sorted(REQUIRED_COLUMNS.difference(frame.columns))
    if missing_required:
        raise ValueError(f"Raw dataset is missing required columns: {missing_required}")

    try:
        frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    except (TypeError, ValueError) as error:
        raise ValueError(f"Could not parse date column as datetime: {error}") from error

    raw_validation = _validate_frame(frame, "Raw dataset")
    original_columns = list(frame.columns)
    original_rows = len(frame)

    # rv1 and rv2 are random/questionable, identical row by row, and have no
    # physical interpretation. No other columns are excluded in this phase.
    processed = frame.drop(columns=list(COLUMNS_TO_REMOVE)).copy()
    # Statistical outliers are retained because unusually high energy consumption may represent legitimate building operation rather than erroneous measurements.

    expected_columns = [column for column in original_columns if column not in COLUMNS_TO_REMOVE]
    if list(processed.columns) != expected_columns:
        raise AssertionError("Processed columns differ from raw columns beyond rv1/rv2 removal")
    if len(processed) != original_rows:
        raise AssertionError("Preprocessing changed the number of observations")

    processed_validation = _validate_frame(processed, "Processed dataset")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    processed.to_csv(
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
    reloaded_validation = _validate_frame(reloaded, "Reloaded processed dataset")
    if list(reloaded.columns) != expected_columns:
        raise AssertionError("Reloaded processed dataset has unexpected columns")
    if len(reloaded) != original_rows:
        raise AssertionError("Reloading the processed CSV changed the number of observations")
    assert_frame_equal(processed, reloaded, check_dtype=False, check_exact=True)

    raw_checksum_after = sha256_file(input_path)
    if raw_checksum_after != raw_checksum_before:
        raise RuntimeError("Raw dataset checksum changed during preprocessing")

    return {
        "input_path": input_path,
        "output_path": output_path,
        "raw_checksum_before": raw_checksum_before,
        "raw_checksum_after": raw_checksum_after,
        "processed_checksum": sha256_file(output_path),
        "raw": raw_validation,
        "processed": processed_validation,
        "reloaded": reloaded_validation,
        "removed_columns": list(COLUMNS_TO_REMOVE),
        "date_format": DATE_FORMAT,
        "columns": list(reloaded.columns),
        "dtypes": {column: str(dtype) for column, dtype in reloaded.dtypes.items()},
        "rows_unchanged": len(reloaded) == original_rows,
    }


def main() -> None:
    report = preprocess_dataset()
    print(f"Raw dataset: {report['input_path']}")
    print(f"Raw shape: {report['raw']['rows']} rows x {report['raw']['columns']} columns")
    print(f"Raw SHA-256 before: {report['raw_checksum_before']}")
    print(f"Raw SHA-256 after:  {report['raw_checksum_after']}")
    print(f"Processed dataset: {report['output_path']}")
    print(
        "Processed shape: "
        f"{report['processed']['rows']} rows x {report['processed']['columns']} columns"
    )
    print(f"Removed columns: {', '.join(report['removed_columns'])}")
    print(f"Rows unchanged: {report['rows_unchanged']}")
    print(f"Missing values: {report['processed']['missing_values']}")
    print(f"Duplicate rows: {report['processed']['duplicate_rows']}")
    print(f"Duplicate timestamps: {report['processed']['duplicate_timestamps']}")
    print(f"Chronologically ordered: {report['processed']['chronologically_ordered']}")
    print(f"Processed SHA-256: {report['processed_checksum']}")
    print("Processed data types:")
    for column, dtype in report["dtypes"].items():
        print(f"  {column}: {dtype}")


if __name__ == "__main__":
    main()