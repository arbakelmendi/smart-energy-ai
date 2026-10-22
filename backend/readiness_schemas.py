"""Factual latest-history compatibility; never a forecast response."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel

ReasonCode = Literal["NO_MEASUREMENTS", "INSUFFICIENT_HISTORY", "LATEST_WINDOW_HAS_GAPS", "INVALID_RAW_DATA", "READY"]

class HistoryGap(BaseModel):
    before_timestamp: datetime
    after_timestamp: datetime
    actual_interval_seconds: float

class PredictionReadiness(BaseModel):
    building_id: int
    ready: bool
    latest_measurement_timestamp: datetime | None
    measurement_count: int
    required_history_intervals: int
    required_observations: int
    continuous_intervals_available: int
    required_interval_minutes: int
    reason_code: ReasonCode
    message: str
    first_gap: HistoryGap | None = None
