import { comparisonSchema, importanceSchema, modelInfoSchema, thresholdsSchema } from "./research-schemas.ts";
import { ApiError } from "./client.ts";
import type { ZodType } from "zod";
import { apiRequest } from "./client.ts";
import type {
  EngineeredFeatures, ForecastRecommendationResponse, ForecastRequest, ForecastResponse,
  HealthResponse, ModelInfoResponse, RecommendationThresholdsResponse, ModelComparisonResponse, FeatureImportanceResponse,
} from "./types.ts";

export const getHealth = (signal?: AbortSignal) => apiRequest<HealthResponse>("/health", signal ? { signal } : {});
export const getModelInfo = (signal?: AbortSignal) => checkedGet<ModelInfoResponse>("/model/info", modelInfoSchema, signal);
export const getRecommendationThresholds = (signal?: AbortSignal) =>
  checkedGet<RecommendationThresholdsResponse>("/recommendations/thresholds", thresholdsSchema, signal);

function post<T>(path: string, features: EngineeredFeatures): Promise<T> {
  // JSON.stringify would silently turn nonfinite numbers into null. Fail explicitly instead.
  if (Object.values(features).some((value) => typeof value !== "number" || !Number.isFinite(value))) {
    return Promise.reject(new TypeError("Engineered features must be finite numeric values."));
  }
  const body: ForecastRequest = { features };
  return apiRequest<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

/** Only valid, already-engineered observations. No histories or fallback data are generated. */
export const forecast = (features: EngineeredFeatures) => post<ForecastResponse>("/forecast", features);
export const forecastWithRecommendation = (features: EngineeredFeatures) =>
  post<ForecastRecommendationResponse>("/forecast/recommendation", features);


async function checkedGet<T>(path: string, schema: ZodType<T>, signal?: AbortSignal): Promise<T> {
  const payload = await apiRequest<unknown>(path, signal ? { signal } : {});
  const parsed = schema.safeParse(payload);
  if (!parsed.success) throw new ApiError("Backend returned malformed research data.", 200);
  return parsed.data;
}
export const getModelComparison = (signal?: AbortSignal) => checkedGet<ModelComparisonResponse>("/analysis/model-comparison", comparisonSchema, signal);
export const getFeatureImportance = (signal?: AbortSignal) => checkedGet<FeatureImportanceResponse>("/analysis/feature-importance", importanceSchema, signal);
