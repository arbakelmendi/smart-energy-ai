"""Dedicated cross-owner oversight queries. Ordinary ownership services stay separate."""
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import case, delete, func, or_, select, update
from .db_models import AuthSession, Building, Measurement, Prediction, User, utc_now


def count(db, model, *conditions):
    return db.scalar(select(func.count()).select_from(model).where(*conditions))


def overview(db):
    total, active, admins = db.execute(select(func.count(User.id),
        func.coalesce(func.sum(case((User.is_active.is_(True), 1), else_=0)), 0),
        func.coalesce(func.sum(case((User.role == 'ADMIN', 1), else_=0)), 0))).one()
    return dict(total_users=total, active_users=active, inactive_users=total-active,
                admin_users=admins, regular_users=total-admins,
                total_buildings=count(db, Building), total_measurements=count(db, Measurement),
                total_predictions=count(db, Prediction))


def owner(row):
    return dict(id=row.id, email=row.email, full_name=row.full_name)


def user_response(row, buildings):
    return dict(**owner(row), role=row.role, is_active=row.is_active,
                created_at=row.created_at, updated_at=row.updated_at, building_count=buildings)


def search_condition(columns, search):
    # Substring search treats SQL wildcard characters literally.
    term=' '.join((search or '').split())
    return or_(*(column.icontains(term, autoescape=True) for column in columns)) if term else None


def users(db, limit, offset, search=None, role=None, is_active=None):
    conditions=[]
    condition=search_condition([User.email, User.full_name], search)
    if condition is not None: conditions.append(condition)
    if role is not None: conditions.append(User.role == role)
    if is_active is not None: conditions.append(User.is_active == is_active)
    counts=select(Building.owner_id, func.count().label('n')).group_by(Building.owner_id).subquery()
    rows=db.execute(select(User, func.coalesce(counts.c.n, 0)).outerjoin(counts, counts.c.owner_id == User.id)
        .where(*conditions).order_by(User.id).limit(limit).offset(offset)).all()
    return dict(items=[user_response(row, n) for row,n in rows], total=count(db, User, *conditions), limit=limit, offset=offset)


def user_detail(db, user_id):
    row=db.get(User, user_id)
    if row is None: raise HTTPException(404, 'User not found')
    owned=select(Building.id).where(Building.owner_id == user_id)
    return dict(**user_response(row, count(db, Building, Building.owner_id == user_id)),
                measurement_count=count(db, Measurement, Measurement.building_id.in_(owned)),
                prediction_count=count(db, Prediction, Prediction.building_id.in_(owned)))


def set_user_status(db, actor, user_id, is_active):
    # Serialize active-administrator changes on databases supporting row locks.
    # The conditional UPDATE also protects the invariant under SQLite's write lock.
    db.execute(select(User.id).where(User.role == 'ADMIN', User.is_active.is_(True))
               .order_by(User.id).with_for_update()).all()
    target=db.get(User, user_id, populate_existing=True)
    if target is None: raise HTTPException(404, 'User not found')
    active_admins=select(func.count(User.id)).where(User.role == 'ADMIN', User.is_active.is_(True)).scalar_subquery()
    if not is_active:
        if target.role == 'ADMIN' and target.is_active and db.scalar(select(active_admins)) <= 1:
            raise HTTPException(409, 'Cannot deactivate the final active administrator')
        if actor.id == user_id:
            raise HTTPException(409, 'Cannot deactivate your own administrator account')
    conditions=[User.id == user_id]
    if not is_active:
        conditions.append(or_(User.role != 'ADMIN', User.is_active.is_(False), active_admins > 1))
    result=db.execute(update(User).where(*conditions).values(is_active=is_active, updated_at=utc_now())
                      .execution_options(synchronize_session=False))
    if result.rowcount != 1:
        raise HTTPException(409, 'Cannot deactivate the final active administrator')
    if not is_active:
        db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
    db.commit()
    db.expire_all()
    return user_detail(db, user_id)


def building_query():
    measurements=select(Measurement.building_id, func.count().label('n'),
        func.min(Measurement.timestamp).label('first'), func.max(Measurement.timestamp).label('last'))
    measurements=measurements.group_by(Measurement.building_id).subquery()
    predictions=select(Prediction.building_id, func.count().label('n'), func.max(Prediction.created_at).label('last'))
    predictions=predictions.group_by(Prediction.building_id).subquery()
    return (select(Building, User, func.coalesce(measurements.c.n, 0), func.coalesce(predictions.c.n, 0),
                   measurements.c.first, measurements.c.last, predictions.c.last)
            .join(User, User.id == Building.owner_id)
            .outerjoin(measurements, measurements.c.building_id == Building.id)
            .outerjoin(predictions, predictions.c.building_id == Building.id))


def building_response(row):
    building, user, measurements, predictions, first, last, predicted=row
    return dict(id=building.id, name=building.name, building_type=building.building_type,
                floor_area_m2=building.floor_area_m2, city=building.city,
                created_at=building.created_at, updated_at=building.updated_at, owner=owner(user),
                measurement_count=measurements, prediction_count=predictions,
                latest_measurement_timestamp=last, latest_prediction_timestamp=predicted)


def buildings(db, limit, offset, search=None, owner_id=None, building_type=None):
    conditions=[]
    condition=search_condition([Building.name, Building.city], search)
    if condition is not None: conditions.append(condition)
    if owner_id is not None: conditions.append(Building.owner_id == owner_id)
    if building_type is not None: conditions.append(Building.building_type == building_type)
    rows=db.execute(building_query().where(*conditions).order_by(Building.id).limit(limit).offset(offset)).all()
    return dict(items=[building_response(row) for row in rows], total=count(db, Building, *conditions), limit=limit, offset=offset)


def prediction_response(prediction, building, user):
    return dict(id=prediction.id, building_id=building.id, building_name=building.name, owner=owner(user),
                source_timestamp=prediction.source_timestamp,
                forecast_timestamp=prediction.source_timestamp+timedelta(minutes=prediction.horizon_minutes),
                prediction_wh=prediction.prediction_wh, horizon_minutes=prediction.horizon_minutes,
                unit='Wh', recommendation_level=prediction.recommendation_level, created_at=prediction.created_at)


def building_detail(db, building_id):
    row=db.execute(building_query().where(Building.id == building_id)).first()
    if row is None: raise HTTPException(404, 'Building not found')
    building, user, _, _, first, _, _=row
    prediction=db.scalar(select(Prediction).where(Prediction.building_id == building_id)
        .order_by(Prediction.created_at.desc(), Prediction.id.desc()).limit(1))
    return dict(**building_response(row), description=building.description,
                earliest_measurement_timestamp=first,
                latest_prediction=prediction_response(prediction, building, user) if prediction else None)


def predictions(db, limit, offset):
    rows=db.execute(select(Prediction, Building, User).join(Building, Building.id == Prediction.building_id)
        .join(User, User.id == Building.owner_id).order_by(Prediction.created_at.desc(), Prediction.id.desc())
        .limit(limit).offset(offset)).all()
    return dict(items=[prediction_response(*row) for row in rows], total=count(db, Prediction), limit=limit, offset=offset)
