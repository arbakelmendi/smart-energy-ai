import { z } from "zod";
import { apiRequest, ApiError } from "./client.ts";
import { buildingSchema } from "./buildings.ts";
import { measurementSchema } from "./measurements.ts";
import { readinessSchema } from "./prediction-readiness.ts";
import { predictionSchema } from "./building-predictions.ts";
const localTime = z
  .string()
  .datetime({ local: true })
  .refine((v) => !/[Zz]|[+-][0-9]{2}:[0-9]{2}$/.test(v));
const summary = z
  .object({
    building: buildingSchema,
    measurement_count: z.number().int().nonnegative(),
    earliest_timestamp: localTime.nullable(),
    latest_timestamp: localTime.nullable(),
    latest_measurement: measurementSchema.nullable(),
    readiness: readinessSchema,
    prediction_count: z.number().int().nonnegative(),
    current_prediction: predictionSchema.nullable(),
    latest_stored_prediction: predictionSchema.nullable(),
    recent_predictions: z.array(predictionSchema).max(5),
    energy_history: z
      .array(z.object({ timestamp: localTime, Appliances: z.number().finite() }).strict())
      .max(500),
    window_limit: z.number().int().positive().max(500),
  })
  .strict();
export type BuildingDashboardSummary = z.infer<typeof summary>;
export const dashboardKeys = {
  building: (userId: number | undefined, id: number) => ["building-dashboard", userId, id] as const,
};
export async function getBuildingDashboardSummary(id: number, limit = 144, signal?: AbortSignal) {
  if (!Number.isSafeInteger(id) || id < 1 || !Number.isInteger(limit) || limit < 1 || limit > 500)
    throw new TypeError("Invalid dashboard building/window");
  const payload = await apiRequest<unknown>(`/buildings/${id}/dashboard-summary?limit=${limit}`, {
    credentials: "include",
    ...(signal ? { signal } : {}),
  });
  const result = summary.safeParse(payload);
  if (!result.success) throw new ApiError("Backend returned malformed dashboard data.", 200);
  const v = result.data;
  const predictions = [
    v.current_prediction,
    v.latest_stored_prediction,
    ...v.recent_predictions,
  ].filter((x) => x !== null);
  if (
    v.building.id !== id ||
    v.readiness.building_id !== id ||
    (v.latest_measurement !== null && v.latest_measurement.building_id !== id) ||
    predictions.some((x) => x.building_id !== id) ||
    (v.current_prediction !== null && !v.current_prediction.matches_current_history)
  )
    throw new ApiError("Backend returned malformed dashboard data.", 200);
  return v;
}
