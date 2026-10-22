"""Owned compatibility status only: no feature preview or forecast endpoint."""
from fastapi import APIRouter, HTTPException
from .buildings import Db, CurrentUser, BuildingId
from .building_service import get_building_for_user
from .prediction_features import assess_prediction_readiness, FeatureContractUnavailable
from .readiness_schemas import PredictionReadiness

router = APIRouter(tags=["prediction readiness"])

@router.get("/buildings/{building_id}/prediction-readiness", response_model=PredictionReadiness)
def readiness(building_id: BuildingId, db: Db, user: CurrentUser):
    get_building_for_user(db, user, building_id)
    try:
        return assess_prediction_readiness(db, building_id).readiness
    except FeatureContractUnavailable:
        raise HTTPException(503, "Verified feature contract is unavailable") from None
