/** Mirrors backend/schemas.py. Numbers are Wh unless the field states otherwise. */
export interface HealthResponse {
  status: "ok" | "unavailable";
  model_available: boolean;
  recommendation_available: boolean;
  forecast_horizon_minutes: number | null;
}

export interface ModelInfoResponse {
  model_name: string;
  model_family: string;
  target: string;
  unit: "Wh";
  forecast_horizon_minutes: number;
  feature_count: number;
  ordered_feature_names: string[];
  final_held_out_metrics: { mae: number; rmse: number; r2: number };
  model_selection_method: string;
  recommendation_capability: string;
  recommendation_available: boolean;
}

/** Exactly 42 real engineered origin-time features; names/validation belong to the backend.
 * The browser does not supply missing lags or rolling history. No raw-sensor form is implied.
 */
export type EngineeredFeatures = Record<string, number>;
export interface ForecastRequest { features: EngineeredFeatures }
export interface ForecastResponse {
  prediction_wh: number;
  forecast_horizon_minutes: number;
  target: string;
  unit: "Wh";
}

export type ConsumptionLevel = "NORMAL" | "ELEVATED" | "HIGH" | "VERY HIGH";
export interface PercentilesWh {
  percentile_50: number;
  percentile_75: number;
  percentile_90: number;
  percentile_95: number;
}
export interface RecommendationThresholdsResponse {
  calibration_dataset: "train+validation";
  calibration_rows: number;
  target_column: string;
  unit: "Wh";
  forecast_horizon_minutes: number;
  percentiles_wh: PercentilesWh;
  level_definitions: Record<ConsumptionLevel, string>;
  test_used: false;
}
export interface ForecastRecommendationResponse {
  prediction: { value_wh: number; horizon_minutes: number; unit: "Wh"; level: ConsumptionLevel };
  thresholds_wh: PercentilesWh;
  trend: {
    current_wh: number;
    change_wh: number;
    change_percent: number | null;
    direction: "rising" | "falling" | "stable";
  };
  recommendation: {
    code: "NORMAL_CONSUMPTION" | "ELEVATED_CONSUMPTION" | "HIGH_CONSUMPTION" | "VERY_HIGH_CONSUMPTION";
    priority: "low" | "medium" | "high";
    title: string;
    message: string;
    rationale: string;
  };
  scope: { automatic_control: false; estimated_savings: null; note: string };
}
