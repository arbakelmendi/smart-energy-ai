"""Persisted forecast/recommendation responses; no engineered client inputs."""
from datetime import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from .schemas import FiniteNumber, Level

Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
VALIDATION_NOTICE = "The forecasting model was validated on the UCI reference building. Predictions for other buildings are experimental."

class EmptyPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

class PredictionRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    level: Level
    code: str
    priority: Literal["low", "medium", "high"]
    text: str

class BuildingPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    building_id: int
    source_timestamp: datetime
    forecast_timestamp: datetime
    prediction_wh: FiniteNumber
    unit: Literal["Wh"] = "Wh"
    horizon_minutes: int
    model_name: str
    model_checksum: Hash
    feature_hash: Hash | None
    current_appliances_wh: FiniteNumber | None
    recommendation: PredictionRecommendation | None
    created_at: datetime
    matches_current_history: bool
    validation_notice: str = VALIDATION_NOTICE

class CreatedBuildingPrediction(BuildingPrediction):
    reused_existing_prediction: bool

class PredictionListResponse(BaseModel):
    items: list[BuildingPrediction]
    total: int
    limit: int
    offset: int
    current_source_timestamp: datetime | None
    current_history_ready: bool
