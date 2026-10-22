import { z } from "zod";
import { ApiError, apiRequest } from "./client.ts";
const timestamp = z
  .string()
  .datetime({ local: true })
  .refine((v) => !/[Zz]|[+-][0-9]{2}:[0-9]{2}$/.test(v));
const hash = z.string().regex(/^[0-9a-f]{64}$/);
const recommendation = z
  .object({
    level: z.enum(["NORMAL", "ELEVATED", "HIGH", "VERY HIGH"]),
    code: z.string().min(1),
    priority: z.enum(["low", "medium", "high"]),
    text: z.string().min(1),
  })
  .strict();
export const predictionSchema = z
  .object({
    id: z.number().int().positive().safe(),
    building_id: z.number().int().positive().safe(),
    source_timestamp: timestamp,
    forecast_timestamp: timestamp,
    prediction_wh: z.number().finite(),
    unit: z.literal("Wh"),
    horizon_minutes: z.number().int().positive(),
    model_name: z.string().min(1),
    model_checksum: hash,
    feature_hash: hash.nullable(),
    current_appliances_wh: z.number().finite().nullable(),
    recommendation: recommendation.nullable(),
    created_at: timestamp,
    matches_current_history: z.boolean(),
    validation_notice: z.string().min(1),
  })
  .strict();
const created = predictionSchema.extend({ reused_existing_prediction: z.boolean() });
const list = z
  .object({
    items: z.array(predictionSchema),
    total: z.number().int().nonnegative(),
    limit: z.number().int().positive().max(500),
    offset: z.number().int().nonnegative(),
    current_source_timestamp: timestamp.nullable(),
    current_history_ready: z.boolean(),
  })
  .strict();
export type BuildingPrediction = z.infer<typeof predictionSchema>;
export type PredictionRecommendation = z.infer<typeof recommendation>;
export type PredictionListResponse = z.infer<typeof list>;
export type CreatedBuildingPrediction = z.infer<typeof created>;
export const predictionKeys = {
  building: (userId: number | undefined, id: number) =>
    ["building-predictions", userId, id] as const,
};
function path(id: number) {
  if (!Number.isSafeInteger(id) || id < 1) throw new TypeError("Invalid building id");
  return `/buildings/${id}/predictions`;
}
function checked<T>(schema: z.ZodType<T>, payload: unknown): T {
  const value = schema.safeParse(payload);
  if (!value.success)
    throw new ApiError("Backend returned malformed building prediction data.", 200);
  return value.data;
}
export async function getBuildingPredictions(
  id: number,
  pagination = { limit: 50, offset: 0 },
  signal?: AbortSignal,
) {
  if (
    !Number.isInteger(pagination.limit) ||
    pagination.limit < 1 ||
    pagination.limit > 500 ||
    !Number.isSafeInteger(pagination.offset) ||
    pagination.offset < 0
  )
    throw new TypeError("Invalid pagination");
  const value = checked(
    list,
    await apiRequest<unknown>(`${path(id)}?limit=${pagination.limit}&offset=${pagination.offset}`, {
      credentials: "include",
      ...(signal ? { signal } : {}),
    }),
  );
  if (value.items.some((item) => item.building_id !== id))
    throw new ApiError("Backend returned malformed building prediction data.", 200);
  return value;
}
export async function createBuildingPrediction(id: number) {
  const value = checked(
    created,
    await apiRequest<unknown>(path(id), {
      method: "POST",
      credentials: "include",
      headers: { "X-SmartEnergy-CSRF": "1" },
      signal: AbortSignal.timeout(30_000),
    }),
  );
  if (
    value.building_id !== id ||
    value.horizon_minutes !== 10 ||
    value.feature_hash === null ||
    value.recommendation === null
  )
    throw new ApiError("Backend returned malformed building prediction data.", 200);
  return value;
}
