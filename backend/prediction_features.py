"""Authoritative latest inference features: bounded DB history + pure assessment.

No model import/load/predict, recommendation call, target requirement or DB write.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
from collections.abc import Mapping, Sequence
import warnings
import numpy as np
import pandas as pd
from pydantic import ValidationError
from sqlalchemy import func, select
from .db_models import Measurement, RAW_MEASUREMENT_COLUMNS
from .measurement_schemas import MeasurementCreate
from .readiness_schemas import HistoryGap, PredictionReadiness
from ml.src.feature_engineering import (
    engineer_origin_features, EXPECTED_INTERVAL, LAG_STEPS, ROLLING_WINDOWS,
    TEMPORAL_FEATURES, CYCLICAL_FEATURES, LAG_FEATURES, ROLLING_FEATURES,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "ml/results/feature_schema.json"
METADATA_PATH = ROOT / "ml/results/final_model_metadata.json"
REQUIRED_HISTORY_INTERVALS = max(max(LAG_STEPS), max(ROLLING_WINDOWS.values()) - 1)
REQUIRED_OBSERVATIONS = REQUIRED_HISTORY_INTERVALS + 1
INTERVAL_MINUTES = int(EXPECTED_INTERVAL.total_seconds() / 60)

class FeatureContractUnavailable(ValueError):
    pass


def ordered_feature_names():
    """Read authoritative order and verify metadata/schema agreement; no model IO."""
    try:
        schema_bytes = SCHEMA_PATH.read_bytes()
        schema = json.loads(schema_bytes)
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        names = tuple(schema["model_feature_columns"])
        implemented = set(RAW_MEASUREMENT_COLUMNS + TEMPORAL_FEATURES + CYCLICAL_FEATURES + LAG_FEATURES + ROLLING_FEATURES)
        valid = (len(names) == len(set(names)) == schema["number_of_model_features"] == metadata["feature_count"] == 42
            and list(names) == metadata["ordered_feature_names"]
            and set(names) == implemented
            and hashlib.sha256(schema_bytes).hexdigest() == metadata["feature_schema_sha256"]
            and schema["forecast_horizon_minutes"] == metadata["forecast_horizon_minutes"] == INTERVAL_MINUTES == 10
            and schema["target_column"] == metadata["target_column"] == "target_appliances_next")
        if not valid:
            raise ValueError("Contract mismatch")
        return names
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise FeatureContractUnavailable("Verified feature contract is unavailable") from exc

@dataclass(frozen=True)
class LatestFeatureRow:
    feature_timestamp: datetime
    feature_names: tuple[str, ...]
    values: tuple[float, ...]

    def as_frame(self):
        # Explicit canonical columns, not dict iteration or inferred input order.
        return pd.DataFrame([self.values], columns=list(self.feature_names))

    def ordered_mapping(self):
        return dict(zip(self.feature_names, self.values, strict=True))

@dataclass(frozen=True)
class FeatureAssessment:
    readiness: PredictionReadiness
    feature_row: LatestFeatureRow | None = None

class HistoryNotReady(ValueError):
    def __init__(self, readiness):
        super().__init__(readiness.message)
        self.readiness = readiness


def assess_history(observations: Sequence[Mapping], *, building_id=0, measurement_count=None):
    """Pure assessment, sorts input and engineers only the latest required window.

    Extra old history is ignored except an equal boundary timestamp (corruption).
    Raw observations use timestamp + exact raw numeric fields, never target data.
    """
    names = ordered_feature_names()
    total = len(observations) if measurement_count is None else measurement_count
    latest = None
    continuous = 0
    def result(code, message, gap=None, feature=None):
        return FeatureAssessment(PredictionReadiness(building_id=building_id, ready=code == "READY",
            latest_measurement_timestamp=latest, measurement_count=total,
            required_history_intervals=REQUIRED_HISTORY_INTERVALS, required_observations=REQUIRED_OBSERVATIONS,
            continuous_intervals_available=continuous, required_interval_minutes=INTERVAL_MINUTES,
            reason_code=code, message=message, first_gap=gap), feature)
    if not observations:
        return result("NO_MEASUREMENTS", "No measurements are stored yet.")
    # Timestamp validity precedes sorting; never silently discard unorderable rows.
    if any(not isinstance(row.get("timestamp"), datetime) or row["timestamp"].tzinfo is not None
           or pd.isna(row["timestamp"]) for row in observations):
        return result("INVALID_RAW_DATA", "Stored history contains an invalid or timezone-aware timestamp.")
    ordered = sorted(observations, key=lambda row: row["timestamp"])
    latest = ordered[-1]["timestamp"]
    window = ordered[-REQUIRED_OBSERVATIONS:]
    if (len(ordered) > len(window) and ordered[-len(window)-1]["timestamp"] == window[0]["timestamp"]
            or any(a["timestamp"] == b["timestamp"] for a, b in zip(window, window[1:]))):
        return result("INVALID_RAW_DATA", "Duplicate timestamps make the latest history ambiguous.")
    # A recent gap is decisive even if deleting a row reduced total below1009.
    gap = None
    for index in range(len(window)-1, 0, -1):
        before, after = window[index-1]["timestamp"], window[index]["timestamp"]
        if after - before != EXPECTED_INTERVAL:
            gap = HistoryGap(before_timestamp=before, after_timestamp=after,
                actual_interval_seconds=(after-before).total_seconds())
            break
        continuous += 1
    try:
        validated = [MeasurementCreate.model_validate({"timestamp": row["timestamp"],
            **{field: row.get(field) for field in RAW_MEASUREMENT_COLUMNS}}).model_dump() for row in window]
    except (ValidationError, ValueError, TypeError, OverflowError):
        return result("INVALID_RAW_DATA", "Required stored raw values are missing, non-numeric or non-finite; no values were filled.")
    if gap is not None:
        return result("LATEST_WINDOW_HAS_GAPS", "The latest history requires exact ten-minute intervals. A gap or incompatible interval was found.", gap)
    if len(window) < REQUIRED_OBSERVATIONS:
        return result("INSUFFICIENT_HISTORY", f"At least {REQUIRED_OBSERVATIONS} continuous observations are required, including the latest row.")
    try:
        latest + timedelta(minutes=INTERVAL_MINUTES)  # Future horizon must be representable; no target required.
        source = pd.DataFrame(validated).rename(columns={"timestamp": "date"})
        source["date"] = pd.to_datetime(source["date"])
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            engineered = engineer_origin_features(source)
        frame = engineered.loc[:, list(names)].iloc[[-1]]
        values = frame.to_numpy(dtype=np.float64)
        if values.shape != (1, 42) or not np.isfinite(values).all():
            return result("INVALID_RAW_DATA", "The latest raw history does not produce a finite complete feature row.")
        feature = LatestFeatureRow(latest, names, tuple(float(value) for value in values[0]))
    except (ValueError, TypeError, OverflowError, RuntimeWarning):
        return result("INVALID_RAW_DATA", "The latest raw history cannot produce a valid feature row.")
    return result("READY", "History is compatible with a ten-minute forecast input. Forecasts run only when explicitly requested.", feature=feature)


def build_latest_feature_row(observations):
    assessment = assess_history(observations)
    if not assessment.readiness.ready:
        raise HistoryNotReady(assessment.readiness)
    return assessment.feature_row


def get_latest_required_history(db, building_id, *, as_of=None):
    """Newest bounded rows then chronological order; one extra guards boundary duplicates.

    as_of is internal for deterministic historical parity checks, not an API option.
    """
    condition = [Measurement.building_id == building_id]
    if as_of is not None:
        condition.append(Measurement.timestamp <= as_of)
    columns = [Measurement.timestamp, *(getattr(Measurement, field) for field in RAW_MEASUREMENT_COLUMNS)]
    rows = db.execute(select(*columns).where(*condition).order_by(Measurement.timestamp.desc(), Measurement.id.desc())
        .limit(REQUIRED_OBSERVATIONS + 1)).mappings().all()
    return [dict(row) for row in reversed(rows)]


def assess_prediction_readiness(db, building_id, *, as_of=None):
    condition = [Measurement.building_id == building_id]
    if as_of is not None:
        condition.append(Measurement.timestamp <= as_of)
    total = db.scalar(select(func.count(Measurement.id)).where(*condition))
    try:
        history = get_latest_required_history(db, building_id, as_of=as_of)
    except (ValueError, TypeError, OverflowError):
        # Defensive corrupt SQLite timestamp handling without raw values/tracebacks.
        ordered_feature_names()
        return FeatureAssessment(PredictionReadiness(building_id=building_id, ready=False,
            latest_measurement_timestamp=None, measurement_count=total,
            required_history_intervals=REQUIRED_HISTORY_INTERVALS, required_observations=REQUIRED_OBSERVATIONS,
            continuous_intervals_available=0, required_interval_minutes=INTERVAL_MINUTES,
            reason_code="INVALID_RAW_DATA", message="Stored timestamps cannot be decoded safely."))
    return assess_history(history, building_id=building_id, measurement_count=total)
