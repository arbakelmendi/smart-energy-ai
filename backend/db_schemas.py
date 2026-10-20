"""Application data DTOs, unused by existing research routes. No auth requests.

Explicit allowlists prevent exposing password_hash via ORM response serialization.
"""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator, model_validator

from .db_models import RAW_MEASUREMENT_COLUMNS

Finite = Annotated[float, Field(strict=True, allow_inf_nan=False)]
PositiveId = Annotated[int, Field(strict=True, gt=0)]


class Record(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class UserRead(Record):
    id: PositiveId
    email: str
    full_name: str
    role: Literal["USER", "ADMIN"]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BuildingData(Record):
    owner_id: PositiveId
    name: str = Field(min_length=1, max_length=200)
    building_type: str | None = Field(default=None, max_length=100)
    floor_area_m2: Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)] | None = None
    city: str | None = Field(default=None, max_length=200)
    description: str | None = None


class Observation(Record):
    building_id: PositiveId
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def naive_observation_time(cls, value):
        if value.tzinfo is not None:
            raise ValueError("Use naive observation time consistently; source timezone is not established")
        return value


MeasurementData = create_model("MeasurementData", __base__=Observation,
                               **{name: (Finite, ...) for name in RAW_MEASUREMENT_COLUMNS})


class PredictionData(Record):
    building_id: PositiveId
    source_timestamp: datetime
    prediction_wh: Finite
    horizon_minutes: Annotated[int, Field(strict=True, gt=0)] = 10
    model_name: str = Field(min_length=1, max_length=200)
    model_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    recommendation_level: Literal["NORMAL", "ELEVATED", "HIGH", "VERY HIGH"] | None = None
    recommendation_code: str | None = None
    recommendation_priority: Literal["low", "medium", "high"] | None = None
    recommendation_text: str | None = None

    @field_validator("source_timestamp")
    @classmethod
    def naive_source_time(cls, value):
        return Observation.naive_observation_time(value)

    @model_validator(mode="after")
    def complete_recommendation(self):
        values = [getattr(self, "recommendation_" + name) for name in ("level", "code", "priority", "text")]
        if any(value is not None for value in values) and any(value is None for value in values):
            raise ValueError("Recommendation snapshot must be wholly present or wholly absent")
        return self
