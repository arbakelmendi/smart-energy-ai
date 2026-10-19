"""Cached production resources and single-row adapters; no fitting or datasets."""
from functools import lru_cache
import logging

import pandas as pd

from ml.src import model_inference as inference
from ml.src import recommendation_engine as recommendations

logger = logging.getLogger(__name__)


class ResourceUnavailable(Exception):
    """An existing production artifact cannot be loaded or verified."""


class InvalidFeatures(Exception):
    """The request does not match the existing engineered-feature contract."""


@lru_cache(maxsize=1)
def model_bundle():
    try:
        return inference.load_final_model()
    except Exception as exc:
        logger.exception("Unable to load verified forecasting resources")
        raise ResourceUnavailable("Forecast model unavailable. Restore the canonical Phase 13 artifact and matching metadata; no fallback model is used.") from exc


@lru_cache(maxsize=1)
def thresholds():
    try:
        return recommendations.load_thresholds()
    except Exception as exc:
        logger.exception("Unable to load recommendation thresholds")
        raise ResourceUnavailable("Recommendation thresholds unavailable. Restore the existing Phase 14 metadata.") from exc


def health():
    metadata = None
    try:
        _, metadata = model_bundle()
    except ResourceUnavailable:
        pass
    try:
        thresholds()
        recommendation_available = True
    except ResourceUnavailable:
        recommendation_available = False
    available = metadata is not None
    return {
        "status": "ok" if available and recommendation_available else "unavailable",
        "model_available": available,
        "recommendation_available": recommendation_available,
        "forecast_horizon_minutes": metadata["forecast_horizon_minutes"] if available else None,
    }


def model_info():
    _, metadata = model_bundle()
    try:
        thresholds()
        recommendation_available = True
    except ResourceUnavailable:
        recommendation_available = False
    return {
        "model_name": metadata["model_name"], "model_family": metadata["model_family"],
        "target": metadata["target_column"], "unit": metadata["prediction_unit"],
        "forecast_horizon_minutes": metadata["forecast_horizon_minutes"],
        "feature_count": metadata["feature_count"],
        "ordered_feature_names": metadata["ordered_feature_names"],
        "final_held_out_metrics": metadata["held_out_test_metrics_from_phase11"],
        "model_selection_method": metadata["model_selection_basis"],
        "recommendation_capability": "Forecast-based decision support; no automatic equipment control or guaranteed savings.",
        "recommendation_available": recommendation_available,
    }


def feature_frame(features, metadata):
    names = metadata["ordered_feature_names"]
    # Compare before ordering so extra or missing JSON keys cannot be discarded.
    missing = sorted(set(names) - features.keys())
    extra = sorted(features.keys() - set(names))
    if missing or extra:
        raise InvalidFeatures(f"Feature set mismatch: missing={missing}; unexpected={extra}")
    try:
        frame = pd.DataFrame([features], columns=names)
        inference.validate_feature_frame(frame, names)
        if frame.Appliances.iloc[0] < 0:
            raise ValueError("Current Appliances energy must be nonnegative")
    except (TypeError, ValueError, OverflowError) as exc:
        raise InvalidFeatures("Features must be finite real numbers with nonnegative current Appliances energy.") from exc
    return frame


def forecast(features):
    bundle = model_bundle()
    metadata = bundle[1]
    frame = feature_frame(features, metadata)
    predicted = inference.predict_next_appliances(frame, bundle)
    return {"prediction_wh": float(predicted.iloc[0]),
            "forecast_horizon_minutes": metadata["forecast_horizon_minutes"],
            "target": metadata["target_column"], "unit": metadata["prediction_unit"]}


def forecast_recommendation(features):
    bundle = model_bundle()
    frame = feature_frame(features, bundle[1])
    return recommendations.predict_and_recommend(frame, model_bundle=bundle, thresholds=thresholds())[0]


def threshold_info():
    metadata = thresholds()
    return {"calibration_dataset": metadata["calibration_dataset"],
            "calibration_rows": metadata["calibration_rows"], "target_column": metadata["target_column"],
            "unit": metadata["unit"], "forecast_horizon_minutes": metadata["forecast_horizon_minutes"],
            "percentiles_wh": {k: metadata[k] for k in ("percentile_50", "percentile_75", "percentile_90", "percentile_95")},
            "level_definitions": metadata["level_definitions"], "test_used": metadata["test_used"]}
