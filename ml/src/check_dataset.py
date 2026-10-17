"""Read-only validation of the local UCI Appliances Energy Prediction CSV."""

import csv
import math
import statistics
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "data" / "raw" / "energydata_complete.csv"
REQUIRED_COLUMNS = ("date", "Appliances")

VARIABLE_GROUPS = {
    "target variable": ("Appliances",),
    "indoor temperature variables": (
        "T1", "T2", "T3", "T4", "T5", "T7", "T8", "T9"
    ),
    "indoor relative humidity variables": (
        "RH_1", "RH_2", "RH_3", "RH_4", "RH_5", "RH_7", "RH_8", "RH_9"
    ),
    "outdoor/weather variables": (
        "T6", "RH_6", "T_out", "Press_mm_hg", "RH_out", "Windspeed",
        "Visibility", "Tdewpoint"
    ),
    "lighting": ("lights",),
    "temporal variable": ("date",),
    "intentionally random/questionable variables": ("rv1", "rv2"),
}


def infer_type(values):
    """Report a simple scalar type inferred from non-empty CSV values."""
    present = [value.strip() for value in values if value is not None and value.strip()]
    if not present:
        return "empty"
    try:
        for value in present:
            int(value)
        return "int"
    except ValueError:
        pass
    try:
        for value in present:
            number = float(value)
            if not math.isfinite(number):
                raise ValueError
        return "float"
    except ValueError:
        return "str"


def parse_timestamp(value):
    if value is None or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip())
    except ValueError:
        return None


def numeric_values(values):
    parsed = []
    invalid = 0
    for value in values:
        if value is None or not value.strip():
            continue
        try:
            number = float(value)
        except ValueError:
            invalid += 1
            continue
        if math.isfinite(number):
            parsed.append(number)
        else:
            invalid += 1
    return parsed, invalid


def main():
    if not DATASET_PATH.is_file():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    with DATASET_PATH.open("r", newline="", encoding="utf-8-sig") as dataset_file:
        reader = csv.DictReader(dataset_file)
        columns = reader.fieldnames or []
        rows = list(reader)

    malformed_rows = [
        row_number
        for row_number, row in enumerate(rows, start=2)
        if None in row or any(row.get(column) is None for column in columns)
    ]

    print(f"Dataset: {DATASET_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Dimensions: {len(rows)} rows x {len(columns)} columns")
    print("Column names:")
    for column in columns:
        print(f"  {column}")

    print("Data types (inferred from CSV values):")
    for column in columns:
        print(f"  {column}: {infer_type([row.get(column) for row in rows])}")

    missing_by_column = {
        column: sum(
            row.get(column) is None or not row[column].strip()
            for row in rows
        )
        for column in columns
    }
    total_missing = sum(missing_by_column.values())
    print("Missing values per column:")
    for column, count in missing_by_column.items():
        print(f"  {column}: {count}")
    print(f"Total missing values: {total_missing}")

    duplicate_rows = sum(Counter(tuple(row.get(column) for column in columns)
                                 for row in rows).values())
    duplicate_rows -= len(set(tuple(row.get(column) for column in columns)
                              for row in rows))
    print(f"Duplicate rows: {duplicate_rows}")
    print(f"Rows with a mismatched number of CSV fields: {len(malformed_rows)}")
    if malformed_rows:
        print(f"  Malformed CSV row examples: {malformed_rows[:10]}")

    issues = []
    missing_required = [column for column in REQUIRED_COLUMNS if column not in columns]
    print(f"date column exists: {'date' in columns}")
    print(f"Appliances target exists: {'Appliances' in columns}")
    if missing_required:
        issues.append(f"Missing required columns: {', '.join(missing_required)}")
    if malformed_rows:
        issues.append(f"{len(malformed_rows)} CSV rows have a mismatched number of fields")

    if "date" in columns:
        timestamps = [parse_timestamp(row.get("date")) for row in rows]
        invalid_timestamps = sum(value is None for value in timestamps)
        print(f"Unparseable or missing date values: {invalid_timestamps}")
        valid_timestamps = [value for value in timestamps if value is not None]
        chronologically_ordered = (
            invalid_timestamps == 0
            and all(left <= right for left, right in zip(timestamps, timestamps[1:]))
        )
        order_status = (
            "yes" if chronologically_ordered else
            "cannot verify (invalid or missing dates)" if invalid_timestamps else "no"
        )
        print(f"Chronologically ordered in file: {order_status}")

        timestamp_counts = Counter(valid_timestamps)
        duplicate_timestamp_count = sum(count - 1 for count in timestamp_counts.values())
        print(f"Duplicate timestamps: {duplicate_timestamp_count}")
        if duplicate_timestamp_count:
            duplicates = [str(value) for value, count in timestamp_counts.items() if count > 1]
            print(f"  Duplicate timestamp examples: {', '.join(duplicates[:5])}")

        adjacent_differences = [
            right - left
            for left, right in zip(timestamps, timestamps[1:])
            if left is not None and right is not None
        ]
        positive_differences = [value for value in adjacent_differences if value > timedelta(0)]
        difference_counts = Counter(positive_differences)
        print("Timestamp differences (most common positive intervals):")
        for difference, count in difference_counts.most_common(10):
            print(f"  {difference}: {count}")

        if difference_counts:
            actual_interval, interval_count = difference_counts.most_common(1)[0]
            irregular = [
                (index + 1, difference)
                for index, difference in enumerate(adjacent_differences)
                if difference != actual_interval
            ]
            print(f"Most common measurement interval: {actual_interval} ({interval_count} occurrences)")
            print(f"Irregular or non-positive adjacent intervals: {len(irregular)}")
            if irregular:
                examples = ", ".join(
                    f"after data row {row_number}: {difference}"
                    for row_number, difference in irregular[:10]
                )
                print(f"  Irregular interval examples: {examples}")
            if irregular:
                issues.append(f"{len(irregular)} irregular or non-positive timestamp intervals")
        else:
            print("Most common measurement interval: unavailable (no positive adjacent differences)")
            print("Irregular or non-positive adjacent intervals: unavailable")

        if invalid_timestamps:
            issues.append(f"{invalid_timestamps} invalid or missing timestamps")
        elif not chronologically_ordered:
            issues.append("Timestamps are not in chronological order")
        if duplicate_timestamp_count:
            issues.append(f"{duplicate_timestamp_count} duplicate timestamps")

    if duplicate_rows:
        issues.append(f"{duplicate_rows} duplicate rows")
    if total_missing:
        issues.append(f"{total_missing} missing values")

    if "Appliances" in columns:
        target_values, invalid_target_count = numeric_values(
            [row.get("Appliances") for row in rows]
        )
        print("Appliances descriptive statistics:")
        if target_values:
            print(f"  Minimum: {min(target_values)}")
            print(f"  Maximum: {max(target_values)}")
            print(f"  Mean: {statistics.mean(target_values)}")
            print(f"  Median: {statistics.median(target_values)}")
            standard_deviation = statistics.stdev(target_values) if len(target_values) > 1 else 0.0
            print(f"  Standard deviation (sample): {standard_deviation}")
        else:
            print("  Unavailable (no valid numeric target values)")
        if invalid_target_count:
            issues.append(f"{invalid_target_count} non-numeric or non-finite Appliances values")

    available_columns = set(columns)
    print("Available variable groups:")
    for group, members in VARIABLE_GROUPS.items():
        available = [column for column in members if column in available_columns]
        print(f"  {group}: {', '.join(available) if available else '(none)'}")
    print("Units: only Press_mm_hg states a unit in its column name (mm Hg); units for other measurements require verification from source metadata.")

    if "rv1" in columns and "rv2" in columns:
        rv1, _ = numeric_values([row.get("rv1") for row in rows])
        rv2, _ = numeric_values([row.get("rv2") for row in rows])
        same_length = len(rv1) == len(rv2) == len(rows)
        identical = same_length and rv1 == rv2
        print(f"rv1 and rv2 identical row by row: {identical}")
        if identical:
            issues.append("rv1 and rv2 contain identical values and should be treated as questionable")

    if not rows:
        issues.append("Dataset contains no data rows")
    print("Dataset integrity issues:")
    if issues:
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("  None detected by these checks")


if __name__ == "__main__":
    main()