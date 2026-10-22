"""Small ownership-scoped repository/service; no ML or measurement operations."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .building_schemas import BuildingCreate, BuildingUpdate
from .db_models import Building, User


def list_buildings_for_user(db: Session, user: User):
    return db.scalars(select(Building).where(Building.owner_id == user.id).order_by(Building.id.asc())).all()


def get_building_for_user(db: Session, user: User, building_id: int):
    building = db.scalar(select(Building).where(Building.id == building_id, Building.owner_id == user.id))
    if building is None:
        raise HTTPException(404, "Building not found")
    return building


def create_building(db: Session, user: User, body: BuildingCreate):
    building = Building(owner_id=user.id, **body.model_dump())
    db.add(building)
    db.commit()
    db.refresh(building)
    return building


def update_building(db: Session, user: User, building_id: int, body: BuildingUpdate):
    building = get_building_for_user(db, user, building_id)
    for name, value in body.model_dump(exclude_unset=True).items():
        setattr(building, name, value)
    db.commit()
    db.refresh(building)
    return building


def delete_building(db: Session, user: User, building_id: int):
    building = get_building_for_user(db, user, building_id)
    db.delete(building)
    db.commit()
