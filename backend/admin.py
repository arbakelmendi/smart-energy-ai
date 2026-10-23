"""Backend-authoritative administration, explicitly separate from owner APIs."""
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Path, Query
from .auth import csrf_guard, require_admin
from .buildings import Db
from .db_models import User
from . import admin_service as service
from .admin_schemas import (AdminOverviewResponse, AdminUserListResponse, AdminUserDetailResponse,
    AdminUserStatusUpdate, AdminBuildingListResponse, AdminBuildingDetailResponse, AdminPredictionListResponse)

router=APIRouter(prefix='/admin', tags=['administration'], dependencies=[Depends(require_admin)])
Admin=Annotated[User, Depends(require_admin)]
Id=Annotated[int, Path(gt=0, le=9223372036854775807)]
Limit=Annotated[int, Query(ge=1, le=200)]
Offset=Annotated[int, Query(ge=0, le=9223372036854775807)]
Search=Annotated[str | None, Query(max_length=200)]

@router.get('/overview', response_model=AdminOverviewResponse)
def overview(db: Db):
    return service.overview(db)

@router.get('/users', response_model=AdminUserListResponse)
def users(db: Db, limit: Limit=50, offset: Offset=0, search: Search=None,
          role: Literal['USER', 'ADMIN'] | None=None, is_active: bool | None=None):
    return service.users(db, limit, offset, search, role, is_active)

@router.get('/users/{user_id}', response_model=AdminUserDetailResponse)
def user_detail(user_id: Id, db: Db):
    return service.user_detail(db, user_id)

@router.patch('/users/{user_id}/status', response_model=AdminUserDetailResponse, dependencies=[Depends(csrf_guard)])
def status(user_id: Id, body: AdminUserStatusUpdate, db: Db, actor: Admin):
    return service.set_user_status(db, actor, user_id, body.is_active)

@router.get('/buildings', response_model=AdminBuildingListResponse)
def buildings(db: Db, limit: Limit=50, offset: Offset=0, search: Search=None,
              owner_id: Annotated[int | None, Query(gt=0, le=9223372036854775807)]=None,
              building_type: Annotated[str | None, Query(max_length=100)]=None):
    return service.buildings(db, limit, offset, search, owner_id, building_type)

@router.get('/buildings/{building_id}', response_model=AdminBuildingDetailResponse)
def building_detail(building_id: Id, db: Db):
    return service.building_detail(db, building_id)

@router.get('/predictions', response_model=AdminPredictionListResponse)
def predictions(db: Db, limit: Limit=50, offset: Offset=0):
    return service.predictions(db, limit, offset)
