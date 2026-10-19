/** Response-shape checks only; no model selection, thresholds or recommendation rules. */
import { z } from "zod";
const finite = z.number().finite();
const metrics = z.object({ mae: finite, rmse: finite, r2: finite });
export const modelInfoSchema = z.object({
  model_name: z.string().min(1), model_family: z.string(), target: z.string(), unit: z.literal("Wh"),
  forecast_horizon_minutes: finite.positive(), feature_count: z.number().int().positive(),
  ordered_feature_names: z.array(z.string()), final_held_out_metrics: metrics,
  model_selection_method: z.string(), recommendation_capability: z.string(), recommendation_available: z.boolean(),
});
const percentiles = z.object({ percentile_50: finite, percentile_75: finite, percentile_90: finite, percentile_95: finite });
export const thresholdsSchema = z.object({
  calibration_dataset: z.literal("train+validation"), calibration_rows: z.number().int().positive(),
  target_column: z.string(), unit: z.literal("Wh"), forecast_horizon_minutes: finite.positive(),
  percentiles_wh: percentiles, level_definitions: z.object({ NORMAL: z.string().min(1), ELEVATED: z.string().min(1), HIGH: z.string().min(1), "VERY HIGH": z.string().min(1) }),
  test_used: z.literal(false),
});
export const comparisonSchema = z.object({
  evaluation_dataset: z.literal("validation"), unit: z.literal("Wh"),
  models: z.array(metrics.extend({ model: z.string().min(1) })).min(1),
  selected_model: z.string().min(1), selection_metric: z.string(), selected_validation_rmse: finite, selection_basis: z.string(),
});
export const importanceSchema = z.object({
  model_name: z.string().min(1), features: z.array(z.object({ feature: z.string().min(1),
    normalized_gain: finite.min(0).max(1), gain_rank: z.number().int().positive(),
    permutation_mean: finite, permutation_std: finite.nonnegative(), permutation_rank: z.number().int().positive() })).min(1),
  gain_dataset: z.string(), permutation_dataset: z.string(), normalized_gain_definition: z.string(),
  permutation_interpretation: z.string(), permutation_std_definition: z.string(), scope_note: z.string(),
});
