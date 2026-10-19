import { apiRequest } from "./client.ts";
import type {
  EngineeredFeatures, ForecastRecommendationResponse, ForecastRequest, ForecastResponse,
  HealthResponse, ModelInfoResponse, RecommendationThresholdsResponse,
} from "./types.ts";

export const getHealth = (signal?: AbortSignal) => apiRequest<HealthResponse>("/health", signal ? { signal } : {});
export const getModelInfo = (signal?: AbortSignal) => apiRequest<ModelInfoResponse>("/model/info", signal ? { signal } : {});
export const getRecommendationThresholds = (signal?: AbortSignal) =>
  apiRequest<RecommendationThresholdsResponse>("/recommendations/thresholds", signal ? { signal } : {});

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
