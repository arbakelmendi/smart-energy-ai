"""Explicit safe administration contracts; no authentication internals."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, StrictBool
from .schemas import FiniteNumber

class AdminOverviewResponse(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    admin_users: int
    regular_users: int
    total_buildings: int
    total_measurements: int
    total_predictions: int

class AdminOwner(BaseModel):
    id: int
    email: str
    full_name: str

class AdminUser(AdminOwner):
    role: Literal['USER', 'ADMIN']
    is_active: bool
    created_at: datetime
    updated_at: datetime
    building_count: int

class AdminUserDetailResponse(AdminUser):
    measurement_count: int
    prediction_count: int

class AdminUserListResponse(BaseModel):
    items: list[AdminUser]
    total: int
    limit: int
    offset: int

class AdminUserStatusUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    is_active: StrictBool

class AdminBuilding(BaseModel):
    id: int
    name: str
    building_type: str | None
    floor_area_m2: FiniteNumber | None
    city: str | None
    created_at: datetime
    updated_at: datetime
    owner: AdminOwner
    measurement_count: int
    prediction_count: int
    latest_measurement_timestamp: datetime | None
    latest_prediction_timestamp: datetime | None

class AdminBuildingListResponse(BaseModel):
    items: list[AdminBuilding]
    total: int
    limit: int
    offset: int

class AdminPrediction(BaseModel):
    id: int
    building_id: int
    building_name: str
    owner: AdminOwner
    source_timestamp: datetime
    forecast_timestamp: datetime
    prediction_wh: FiniteNumber
    horizon_minutes: int
    unit: Literal['Wh'] = 'Wh'
    recommendation_level: str | None
    created_at: datetime

class AdminPredictionListResponse(BaseModel):
    items: list[AdminPrediction]
    total: int
    limit: int
    offset: int

class AdminBuildingDetailResponse(AdminBuilding):
    description: str | None
    earliest_measurement_timestamp: datetime | None
    latest_prediction: AdminPrediction | None
