"""Native-model inference on already-engineered, schema-ordered features only."""
from __future__ import annotations

import hashlib
from importlib.metadata import version
import json
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_complex_dtype, is_bool_dtype
from xgboost import XGBRegressor

ROOT = Path(__file__).resolve().parents[2]
METADATA_PATH = ROOT / "ml/results/final_model_metadata.json"
ARTIFACT_PATH = ROOT / "ml/models/final_xgboost_model.json"


def read_json(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_metadata(metadata_path=METADATA_PATH):
    """Validate the trackable contract against committed schema and model lock."""
    metadata = read_json(metadata_path)
    schema_path = ROOT / "ml/results/feature_schema.json"
    lock_path = ROOT / "ml/results/phase11_selection_lock.json"
    schema, lock = read_json(schema_path), read_json(lock_path)
    if (metadata["model_name"] != "Tuned XGBoost" or metadata["model_family"] != "XGBoost"
        or metadata["model_format"] != "XGBoost native JSON"
        or metadata["feature_count"] != 42
        or metadata["ordered_feature_names"] != schema["model_feature_columns"]
        or metadata["ordered_feature_names"] != lock["feature_columns"]
        or len(set(metadata["ordered_feature_names"])) != 42
        or metadata["locked_hyperparameters"] != lock["selected_hyperparameters"]
        or metadata["target_column"] != schema["target_column"]
        or metadata["target_column"] != "target_appliances_next"
        or metadata["forecast_horizon_minutes"] != 10
        or metadata["prediction_unit"] != "Wh"
        or metadata["test_used_for_fitting"] is not False):
        raise ValueError("Production metadata does not match the locked feature/model contract")
    if sha256(schema_path) != metadata["feature_schema_sha256"] or sha256(lock_path) != metadata["selection_lock_sha256"]:
        raise ValueError("Production schema/selection lock checksum mismatch")
    artifact = (ROOT / metadata["model_artifact_relative_path"]).resolve()
    if artifact != ARTIFACT_PATH.resolve():
        raise ValueError("Metadata must reference the canonical native model artifact")
    return metadata


def validate_feature_frame(frame, feature_names=None):
    """Require exactly the ordered schema and real, finite numeric observations.

    No coercion, reordering, imputation or raw-data feature engineering occurs.
    """
    if feature_names is None:
        feature_names = read_json(ROOT / "ml/results/feature_schema.json")["model_feature_columns"]
    if len(feature_names) != 42 or len(set(feature_names)) != 42:
        raise ValueError("Expected the 42-feature model contract")
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("Model features must be supplied as a pandas DataFrame")
    if frame.empty:
        raise ValueError("Feature frame must contain at least one observation")
    if frame.columns.duplicated().any():
        raise ValueError("Duplicate feature names are not allowed")
    missing = [name for name in feature_names if name not in frame.columns]
    unexpected = [name for name in frame.columns if name not in feature_names]
    if missing or unexpected:
        raise ValueError(f"Feature set mismatch: missing={missing}; unexpected={unexpected}")
    if frame.columns.tolist() != list(feature_names):
        raise ValueError("Feature order differs from the committed schema")
    invalid = [name for name in feature_names if not is_numeric_dtype(frame[name].dtype)
               or is_complex_dtype(frame[name].dtype) or is_bool_dtype(frame[name].dtype)]
    if invalid:
        raise TypeError(f"Features must contain real numeric values (no string coercion): {invalid}")
    if frame.isna().any().any() or not np.isfinite(frame.to_numpy(dtype=np.float64)).all():
        raise ValueError("Feature values must be finite: NaN/inf values are not allowed")
    return frame


def load_final_model(metadata_path=METADATA_PATH):
    """Return (loaded XGBRegressor, metadata); never access training/test data."""
    metadata = load_metadata(metadata_path)
    if not ARTIFACT_PATH.is_file():
        raise FileNotFoundError("Native artifact missing; run python ml/src/save_final_model.py")
    if sha256(ARTIFACT_PATH) != metadata["model_artifact_sha256"]:
        raise ValueError("Native model artifact checksum mismatch")
    if version("xgboost") != metadata["xgboost_version"]:
        raise ValueError("Use the recorded XGBoost version for verified inference")
    model = XGBRegressor(**metadata["locked_hyperparameters"])
    model.load_model(ARTIFACT_PATH)
    if model.get_booster().feature_names != metadata["ordered_feature_names"] or model.n_features_in_ != 42:
        raise ValueError("Native artifact feature order/count mismatch")
    return model, metadata


def predict_next_appliances(frame, model_bundle=None):
    """Return numeric Wh forecasts at t+10 minutes, preserving row order/index.

    Pass a bundle from load_final_model() to reuse the model across calls.
    Inputs must already contain real current readings and valid historical
    features. Predictions are not clipped; no intervals/scores are invented.
    """
    model, metadata = load_final_model() if model_bundle is None else model_bundle
    validate_feature_frame(frame, metadata["ordered_feature_names"])
    predicted = np.asarray(model.predict(frame))
    if predicted.shape != (len(frame),) or not np.isfinite(predicted).all():
        raise ValueError("Model produced invalid predictions")
    output = pd.Series(predicted, index=frame.index, name="predicted_appliances_next_wh")
    output.attrs = {"unit": "Wh", "forecast_horizon_minutes": metadata["forecast_horizon_minutes"]}
    return output
