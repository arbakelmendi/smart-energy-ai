"""Stored-history inference with shared resources, atomic snapshots and idempotency."""
from datetime import timedelta
import hashlib
import json
import logging
import math
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from . import services
from .db_models import Prediction
from .prediction_features import assess_prediction_readiness, FeatureContractUnavailable
from .building_prediction_schemas import BuildingPrediction, CreatedBuildingPrediction
from .schemas import RecommendationResponse

logger = logging.getLogger(__name__)


def feature_snapshot(feature_row):
    """Canonical names/float64 values only; no user/session/building metadata."""
    snapshot = json.dumps({"feature_names": list(feature_row.feature_names), "feature_values": list(feature_row.values)},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return snapshot, hashlib.sha256(snapshot.encode("utf-8")).hexdigest()


def assess(db, building_id):
    try:
        return assess_prediction_readiness(db, building_id)
    except FeatureContractUnavailable:
        raise HTTPException(503, "Verified feature contract is unavailable") from None


def require_ready(assessment):
    if not assessment.readiness.ready:
        raise HTTPException(409, assessment.readiness.model_dump(mode="json"))


def find_existing(db, building_id, source, checksum, feature_hash):
    return db.scalar(select(Prediction).where(Prediction.building_id == building_id,
        Prediction.source_timestamp == source, Prediction.model_checksum == checksum, Prediction.feature_hash == feature_hash))


def response(row, *, matches=False, reused=None):
    current = None
    if row.feature_snapshot_json is not None:
        try:
            snapshot = json.loads(row.feature_snapshot_json)
            if hashlib.sha256(row.feature_snapshot_json.encode("utf-8")).hexdigest() != row.feature_hash:
                raise ValueError("Snapshot hash mismatch")
            values = snapshot["feature_values"]
            names = snapshot["feature_names"]
            if len(names) != 42 or len(values) != 42 or len(set(names)) != 42 or not all(type(v) in (int,float) and math.isfinite(v) for v in values):
                raise ValueError("Invalid snapshot")
            current = values[names.index("Appliances")]
        except (ValueError, TypeError, KeyError, IndexError):
            raise HTTPException(503, "Stored prediction snapshot is unavailable") from None
    recommendation = None
    if row.recommendation_level is not None:
        recommendation = {"level":row.recommendation_level,"code":row.recommendation_code,
            "priority":row.recommendation_priority,"text":row.recommendation_text}
    body = {"id":row.id,"building_id":row.building_id,"source_timestamp":row.source_timestamp,
        "forecast_timestamp":row.source_timestamp+timedelta(minutes=row.horizon_minutes),
        "prediction_wh":row.prediction_wh,"horizon_minutes":row.horizon_minutes,"unit":"Wh",
        "model_name":row.model_name,"model_checksum":row.model_checksum,"feature_hash":row.feature_hash,
        "current_appliances_wh":current,"recommendation":recommendation,"created_at":row.created_at,
        "matches_current_history":matches}
    if reused is not None:
        return CreatedBuildingPrediction(**body,reused_existing_prediction=reused)
    return BuildingPrediction(**body)


def create_prediction(db, building_id):
    assessment = assess(db, building_id)
    require_ready(assessment)
    feature_row = assessment.feature_row
    frame = feature_row.as_frame()
    if frame.Appliances.iloc[0] < 0:
        raise HTTPException(422, "Current Appliances energy must be nonnegative for the existing recommendation policy")
    bundle = services.model_bundle()  # Existing verified, cached native artifact loader.
    metadata = bundle[1]
    services.inference.validate_feature_frame(frame, metadata["ordered_feature_names"])
    snapshot, fingerprint = feature_snapshot(feature_row)
    source, checksum = feature_row.feature_timestamp, metadata["model_artifact_sha256"]
    existing = find_existing(db, building_id, source, checksum, fingerprint)
    if existing is not None:
        return response(existing,matches=True,reused=True)
    try:
        # Same authoritative integrated helper as the research recommendation API.
        result = services.recommendations.predict_and_recommend(frame, model_bundle=bundle, thresholds=services.thresholds())[0]
        validated = RecommendationResponse.model_validate(result)
        predicted = validated.prediction.value_wh
        if not math.isfinite(predicted) or validated.prediction.horizon_minutes != 10 or validated.prediction.unit != "Wh":
            raise ValueError("Invalid model result")
    except services.ResourceUnavailable:
        raise
    except Exception as exc:
        logger.error("Building forecast or recommendation failed",exc_info=exc)
        raise HTTPException(503, "Forecast or recommendation execution failed; no result was stored") from None
    # Detect changes during inference as well as stale frontend readiness before it.
    checked = assess(db, building_id)
    require_ready(checked)
    if checked.feature_row.feature_timestamp != source or feature_snapshot(checked.feature_row)[1] != fingerprint:
        raise HTTPException(409, {"reason_code":"HISTORY_CHANGED","message":"Stored history changed during forecasting. Retry using current history."})
    row = Prediction(building_id=building_id,source_timestamp=source,prediction_wh=predicted,
        horizon_minutes=10,model_name=metadata["model_name"],model_checksum=checksum,
        feature_hash=fingerprint,feature_snapshot_json=snapshot,
        recommendation_level=validated.prediction.level,recommendation_code=validated.recommendation.code,
        recommendation_priority=validated.recommendation.priority,recommendation_text=validated.recommendation.message)
    try:
        db.add(row)
        db.flush()
        mapped = response(row,matches=True,reused=False)  # Validate before commit.
        db.commit()
        return mapped
    except IntegrityError:
        db.rollback()
        winner = find_existing(db,building_id,source,checksum,fingerprint)
        if winner is not None:
            return response(winner,matches=True,reused=True)
        raise HTTPException(503,"Prediction could not be stored; retry after verifying database availability") from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503,"Prediction could not be stored; no successful persistence is confirmed") from None
    except Exception:
        db.rollback()
        raise


def list_predictions(db, building_id, limit, offset):
    # History stays readable without loading/using model or threshold resources.
    total = db.scalar(select(func.count(Prediction.id)).where(Prediction.building_id == building_id))
    rows = db.scalars(select(Prediction).where(Prediction.building_id == building_id)
        .order_by(Prediction.created_at.desc(),Prediction.id.desc()).limit(limit).offset(offset)).all()
    latest, fingerprint, checksum, ready = None, None, None, False
    try:
        assessed = assess_prediction_readiness(db,building_id)
        latest, ready = assessed.readiness.latest_measurement_timestamp, assessed.readiness.ready
        if ready:
            fingerprint = feature_snapshot(assessed.feature_row)[1]
            checksum = services.inference.load_metadata()["model_artifact_sha256"]  # Metadata only; artifact may be absent.
    except (FeatureContractUnavailable,OSError,ValueError,KeyError):
        ready = False
    return {"items":[response(row,matches=bool(ready and row.feature_hash is not None and
        row.source_timestamp==latest and row.feature_hash==fingerprint and row.model_checksum==checksum and row.horizon_minutes==10)) for row in rows],
        "total":total,"limit":limit,"offset":offset,"current_source_timestamp":latest,"current_history_ready":ready}
