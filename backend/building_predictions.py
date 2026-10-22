"""Owned application forecasts: no frontend-engineered feature body."""
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from .auth import csrf_guard
from .buildings import Db, CurrentUser, BuildingId
from .building_service import get_building_for_user
from .building_prediction_schemas import EmptyPredictionRequest, CreatedBuildingPrediction, PredictionListResponse
from . import building_prediction_service as service

router=APIRouter(prefix="/buildings/{building_id}/predictions",tags=["building predictions"])

@router.post("",response_model=CreatedBuildingPrediction,dependencies=[Depends(csrf_guard)])
def create(building_id:BuildingId,db:Db,user:CurrentUser,body:EmptyPredictionRequest|None=None):
    get_building_for_user(db,user,building_id)
    return service.create_prediction(db,building_id)

@router.get("",response_model=PredictionListResponse)
def listing(building_id:BuildingId,db:Db,user:CurrentUser,
            limit:Annotated[int,Query(ge=1,le=500)]=50,
            offset:Annotated[int,Query(ge=0,le=9223372036854775807)]=0):
    get_building_for_user(db,user,building_id)
    return service.list_predictions(db,building_id,limit,offset)
