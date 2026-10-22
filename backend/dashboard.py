"""Bounded persisted building summary; no model execution or research analytics."""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from .building_prediction_schemas import BuildingPrediction
from .building_prediction_service import current_prediction, prediction_context, response
from .building_schemas import BuildingResponse
from .building_service import get_building_for_user
from .buildings import BuildingId, CurrentUser, Db
from .db_models import Measurement, Prediction
from .measurement_schemas import MeasurementResponse
from .prediction_features import FeatureContractUnavailable, assess_prediction_readiness
from .readiness_schemas import PredictionReadiness
from .schemas import FiniteNumber


class EnergyPoint(BaseModel):
    timestamp: datetime
    Appliances: FiniteNumber


class BuildingDashboardSummary(BaseModel):
    building: BuildingResponse
    measurement_count: int
    earliest_timestamp: datetime | None
    latest_timestamp: datetime | None
    latest_measurement: MeasurementResponse | None
    readiness: PredictionReadiness
    prediction_count: int
    current_prediction: BuildingPrediction | None
    latest_stored_prediction: BuildingPrediction | None
    recent_predictions: list[BuildingPrediction]
    energy_history: list[EnergyPoint]
    window_limit: int


def dashboard_summary(db, building, limit):
    bid = building.id
    count, first, last = db.execute(
        select(func.count(Measurement.id), func.min(Measurement.timestamp),
               func.max(Measurement.timestamp)).where(Measurement.building_id == bid)
    ).one()
    latest = db.scalar(
        select(Measurement).where(Measurement.building_id == bid)
        .order_by(Measurement.timestamp.desc(), Measurement.id.desc()).limit(1)
    )
    points = db.execute(
        select(Measurement.timestamp, Measurement.Appliances)
        .where(Measurement.building_id == bid)
        .order_by(Measurement.timestamp.desc(), Measurement.id.desc()).limit(limit)
    ).all()
    assessment = assess_prediction_readiness(db, bid)
    context = prediction_context(db, bid, assessment)
    current = current_prediction(db, bid, context)
    prediction_count = db.scalar(
        select(func.count(Prediction.id)).where(Prediction.building_id == bid)
    )
    recent = db.scalars(
        select(Prediction).where(Prediction.building_id == bid)
        .order_by(Prediction.created_at.desc(), Prediction.id.desc()).limit(5)
    ).all()
    mapped = [response(row, matches=context.matches(row)) for row in recent]
    return BuildingDashboardSummary(
        building=BuildingResponse.model_validate(building),
        measurement_count=count, earliest_timestamp=first, latest_timestamp=last,
        latest_measurement=MeasurementResponse.model_validate(latest) if latest else None,
        readiness=assessment.readiness, prediction_count=prediction_count,
        current_prediction=response(current, matches=True) if current else None,
        latest_stored_prediction=mapped[0] if mapped else None,
        recent_predictions=mapped,
        energy_history=[EnergyPoint(timestamp=stamp, Appliances=value)
                        for stamp, value in reversed(points)],
        window_limit=limit,
    )


router = APIRouter(tags=["building dashboard"])


@router.get("/buildings/{building_id}/dashboard-summary", response_model=BuildingDashboardSummary)
def summary(building_id: BuildingId, db: Db, user: CurrentUser,
            limit: Annotated[int, Query(ge=1, le=500)] = 144):
    building = get_building_for_user(db, user, building_id)
    try:
        return dashboard_summary(db, building, limit)
    except FeatureContractUnavailable:
        raise HTTPException(503, "Verified feature contract is unavailable") from None
    except (ValueError, TypeError, OverflowError):
        raise HTTPException(503, "Stored building summary is unavailable") from None
