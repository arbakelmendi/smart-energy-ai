"""Owned measurement routes; same-owner ADMIN policy retained."""
from typing import Annotated
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from starlette.concurrency import run_in_threadpool
from .buildings import Db, CurrentUser, BuildingId
from .auth import csrf_guard
from .building_service import get_building_for_user
from .measurement_schemas import MeasurementCreate, MeasurementResponse, MeasurementListResponse, MeasurementImportResponse
from . import measurement_service as service

router = APIRouter(prefix="/buildings/{building_id}/measurements", tags=["measurements"])

@router.post("", response_model=MeasurementResponse, status_code=201, dependencies=[Depends(csrf_guard)])
def create(building_id: BuildingId, body: MeasurementCreate, db: Db, user: CurrentUser):
    get_building_for_user(db, user, building_id)
    return service.create_measurement(db, building_id, body)

@router.get("", response_model=MeasurementListResponse)
def listing(building_id: BuildingId, db: Db, user: CurrentUser,
            limit: Annotated[int, Query(ge=1, le=500)] = 100,
            offset: Annotated[int, Query(ge=0, le=9223372036854775807)] = 0):
    get_building_for_user(db, user, building_id)
    return service.list_measurements(db, building_id, limit, offset)

@router.delete("/{measurement_id}", status_code=204, dependencies=[Depends(csrf_guard)])
def delete(building_id: BuildingId, measurement_id: BuildingId, db: Db, user: CurrentUser):
    get_building_for_user(db, user, building_id)
    service.delete_measurement(db, building_id, measurement_id)
    return Response(status_code=204)

@router.post("/import", response_model=MeasurementImportResponse, dependencies=[Depends(csrf_guard)])
async def import_csv(building_id: BuildingId, db: Db, user: CurrentUser, file: UploadFile = File(...)):
    try:
        await run_in_threadpool(get_building_for_user, db, user, building_id)
        data = await file.read(service.MAX_BYTES + 1)
        if len(data) > service.MAX_BYTES:
            raise HTTPException(413, "CSV exceeds 16 MiB limit")
        def import_sync():
            rows, ignored = service.parse_csv(data)
            return service.persist_rows(db, building_id, rows, ignored)
        return await run_in_threadpool(import_sync)
    finally:
        await file.close()
