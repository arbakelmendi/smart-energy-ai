"""Typed public API contract; feature names remain owned by the ML schema."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Level = Literal["NORMAL", "ELEVATED", "HIGH", "VERY HIGH"]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ForecastRequest(ApiModel):
    features: dict[str, FiniteNumber] = Field(
        description="Exactly the 42 engineered features in the committed feature schema. JSON key order is irrelevant; current readings and valid lags/rolling history are required. Numeric strings and booleans are rejected."
    )


class HealthResponse(ApiModel):
    status: Literal["ok", "unavailable"]
    model_available: bool
    recommendation_available: bool
    forecast_horizon_minutes: int | None


class ForecastResponse(ApiModel):
    prediction_wh: FiniteNumber
    forecast_horizon_minutes: int
    target: str
    unit: Literal["Wh"]


class Prediction(ApiModel):
    value_wh: FiniteNumber
    horizon_minutes: int
    unit: Literal["Wh"]
    level: Level


class Percentiles(ApiModel):
    percentile_50: FiniteNumber
    percentile_75: FiniteNumber
    percentile_90: FiniteNumber
    percentile_95: FiniteNumber


class Trend(ApiModel):
    current_wh: FiniteNumber
    change_wh: FiniteNumber
    change_percent: FiniteNumber | None
    direction: Literal["rising", "falling", "stable"]


class Recommendation(ApiModel):
    code: Literal["NORMAL_CONSUMPTION", "ELEVATED_CONSUMPTION", "HIGH_CONSUMPTION", "VERY_HIGH_CONSUMPTION"]
    priority: Literal["low", "medium", "high"]
    title: str
    message: str
    rationale: str


class Scope(ApiModel):
    automatic_control: Literal[False]
    estimated_savings: None
    note: str


class RecommendationResponse(ApiModel):
    prediction: Prediction
    thresholds_wh: Percentiles
    trend: Trend
    recommendation: Recommendation
    scope: Scope


class Metrics(ApiModel):
    mae: FiniteNumber
    rmse: FiniteNumber
    r2: FiniteNumber


class ModelInfoResponse(ApiModel):
    model_name: str
    model_family: str
    target: str
    unit: Literal["Wh"]
    forecast_horizon_minutes: int
    feature_count: int
    ordered_feature_names: list[str]
    final_held_out_metrics: Metrics
    model_selection_method: str
    recommendation_capability: str
    recommendation_available: bool


class ThresholdResponse(ApiModel):
    calibration_dataset: Literal["train+validation"]
    calibration_rows: int
    target_column: str
    unit: Literal["Wh"]
    forecast_horizon_minutes: int
    percentiles_wh: Percentiles
    level_definitions: dict[Level, str]
    test_used: Literal[False]


class RootResponse(ApiModel):
    name: str
    version: str
    docs: str


class ValidationModel(ApiModel):
    model: str
    mae: FiniteNumber
    rmse: FiniteNumber
    r2: FiniteNumber


class ModelComparisonResponse(ApiModel):
    evaluation_dataset: Literal["validation"]
    unit: Literal["Wh"]
    models: list[ValidationModel]
    selected_model: str
    selection_metric: str
    selected_validation_rmse: FiniteNumber
    selection_basis: str


class FeatureImportanceItem(ApiModel):
    feature: str
    normalized_gain: FiniteNumber
    gain_rank: int
    permutation_mean: FiniteNumber
    permutation_std: FiniteNumber
    permutation_rank: int


class FeatureImportanceResponse(ApiModel):
    model_name: str
    features: list[FeatureImportanceItem]
    gain_dataset: str
    permutation_dataset: str
    normalized_gain_definition: str
    permutation_interpretation: str
    permutation_std_definition: str
    scope_note: str
