import { z } from "zod";
import { ApiError, apiRequest } from "./client.ts";
export const readinessCodes = [
  "NO_MEASUREMENTS",
  "INSUFFICIENT_HISTORY",
  "LATEST_WINDOW_HAS_GAPS",
  "INVALID_RAW_DATA",
  "READY",
] as const;
const localTimestamp = z
  .string()
  .datetime({ local: true })
  .refine((value) => !/[Zz]|[+-][0-9]{2}:[0-9]{2}$/.test(value));
const gapSchema = z
  .object({
    before_timestamp: localTimestamp,
    after_timestamp: localTimestamp,
    actual_interval_seconds: z.number().finite().positive(),
  })
  .strict();
export const readinessSchema = z
  .object({
    building_id: z.number().int().positive().safe(),
    ready: z.boolean(),
    latest_measurement_timestamp: localTimestamp.nullable(),
    measurement_count: z.number().int().nonnegative().safe(),
    required_history_intervals: z.number().int().positive(),
    required_observations: z.number().int().positive(),
    continuous_intervals_available: z.number().int().nonnegative(),
    required_interval_minutes: z.literal(10),
    reason_code: z.enum(readinessCodes),
    message: z.string().min(1),
    first_gap: gapSchema.nullable(),
  })
  .strict()
  .refine(
    (value) =>
      value.ready === (value.reason_code === "READY") &&
      value.required_observations === value.required_history_intervals + 1 &&
      value.continuous_intervals_available <= value.required_history_intervals &&
      (!value.ready || value.latest_measurement_timestamp !== null),
    "Inconsistent readiness response",
  );
export type PredictionReadiness = z.infer<typeof readinessSchema>;
export const readinessKeys = {
  building: (userId: number | undefined, buildingId: number) =>
    ["prediction-readiness", userId, buildingId] as const,
};
export async function getPredictionReadiness(
  buildingId: number,
  signal?: AbortSignal,
): Promise<PredictionReadiness> {
  if (!Number.isSafeInteger(buildingId) || buildingId < 1)
    throw new TypeError("Invalid building id");
  const payload = await apiRequest<unknown>(`/buildings/${buildingId}/prediction-readiness`, {
    credentials: "include",
    ...(signal ? { signal } : {}),
  });
  const parsed = readinessSchema.safeParse(payload);
  if (!parsed.success || parsed.data.building_id !== buildingId)
    throw new ApiError("Backend returned malformed prediction readiness.", 200);
  return parsed.data;
}
