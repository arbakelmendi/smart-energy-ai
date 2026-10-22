"""Authenticated owner-only CRUD; ADMIN has the same ownership policy here."""
from typing import Annotated
from fastapi import APIRouter, Depends, Path, Response
from sqlalchemy.orm import Session
from .auth import csrf_guard, get_current_user
from .database import get_db
from .db_models import User
from .building_schemas import BuildingCreate, BuildingUpdate, BuildingResponse, BuildingListResponse
from . import building_service as service

router = APIRouter(prefix="/buildings", tags=["buildings"])
Db = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
BuildingId = Annotated[int, Path(gt=0, le=9223372036854775807)]


@router.post("", response_model=BuildingResponse, status_code=201, dependencies=[Depends(csrf_guard)])
def create(body: BuildingCreate, db: Db, user: CurrentUser):
    return service.create_building(db, user, body)


@router.get("", response_model=BuildingListResponse)
def listing(db: Db, user: CurrentUser):
    return {"buildings": service.list_buildings_for_user(db, user)}


@router.get("/{building_id}", response_model=BuildingResponse)
def detail(building_id: BuildingId, db: Db, user: CurrentUser):
    return service.get_building_for_user(db, user, building_id)


@router.patch("/{building_id}", response_model=BuildingResponse, dependencies=[Depends(csrf_guard)])
def update(building_id: BuildingId, body: BuildingUpdate, db: Db, user: CurrentUser):
    return service.update_building(db, user, building_id, body)


@router.delete("/{building_id}", status_code=204, dependencies=[Depends(csrf_guard)])
def delete(building_id: BuildingId, db: Db, user: CurrentUser):
    service.delete_building(db, user, building_id)
    return Response(status_code=204)
