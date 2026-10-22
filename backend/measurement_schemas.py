"""Raw observations only; no engineered features or timezone assumptions."""
from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, field_validator

Finite = Annotated[float, Field(strict=True, allow_inf_nan=False)]

class MeasurementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timestamp: datetime
    Appliances: Finite
    lights: Finite
    T1: Finite
    RH_1: Finite
    T2: Finite
    RH_2: Finite
    T3: Finite
    RH_3: Finite
    T4: Finite
    RH_4: Finite
    T5: Finite
    RH_5: Finite
    T6: Finite
    RH_6: Finite
    T7: Finite
    RH_7: Finite
    T8: Finite
    RH_8: Finite
    T9: Finite
    RH_9: Finite
    T_out: Finite
    Press_mm_hg: Finite
    RH_out: Finite
    Windspeed: Finite
    Visibility: Finite
    Tdewpoint: Finite

    @field_validator("timestamp", mode="before")
    @classmethod
    def local_timestamp(cls, value):
        if isinstance(value, str):
            if len(value) < 16 or value[10] not in ("T", " "):
                raise ValueError("Use an ISO-8601 local timestamp with date and time, without timezone")
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                raise ValueError("Invalid ISO-8601 timestamp") from None
        if not isinstance(value, datetime) or value.tzinfo is not None:
            raise ValueError("Timestamp must be timezone-naive building-local time; offsets/Z are not accepted")
        return value

class MeasurementResponse(MeasurementCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    building_id: int

class MeasurementListResponse(BaseModel):
    items: list[MeasurementResponse]
    total: int
    limit: int
    offset: int
    first_timestamp: datetime | None
    last_timestamp: datetime | None

class MeasurementImportResponse(BaseModel):
    building_id: int
    rows_received: int
    rows_imported: int
    first_timestamp: datetime
    last_timestamp: datetime
    ignored_columns: list[str]
