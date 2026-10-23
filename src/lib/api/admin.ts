import { z } from "zod";
import { apiRequest, ApiError } from "./client.ts";
const id = z.number().int().positive().safe();
const count = z.number().int().nonnegative().safe();
const timestamp = z.string().datetime({ local: true });
const owner = z.object({ id, email: z.string(), full_name: z.string() }).strict();
const user = owner
  .extend({
    role: z.enum(["USER", "ADMIN"]),
    is_active: z.boolean(),
    created_at: timestamp,
    updated_at: timestamp,
    building_count: count,
  })
  .strict();
const userDetail = user.extend({ measurement_count: count, prediction_count: count }).strict();
const building = z
  .object({
    id,
    name: z.string(),
    building_type: z.string().nullable(),
    floor_area_m2: z.number().finite().nullable(),
    city: z.string().nullable(),
    created_at: timestamp,
    updated_at: timestamp,
    owner,
    measurement_count: count,
    prediction_count: count,
    latest_measurement_timestamp: timestamp.nullable(),
    latest_prediction_timestamp: timestamp.nullable(),
  })
  .strict();
const prediction = z
  .object({
    id,
    building_id: id,
    building_name: z.string(),
    owner,
    source_timestamp: timestamp,
    forecast_timestamp: timestamp,
    prediction_wh: z.number().finite(),
    horizon_minutes: z.number().int().positive(),
    unit: z.literal("Wh"),
    recommendation_level: z.enum(["NORMAL", "ELEVATED", "HIGH", "VERY HIGH"]).nullable(),
    created_at: timestamp,
  })
  .strict();
const buildingDetail = building
  .extend({
    description: z.string().nullable(),
    earliest_measurement_timestamp: timestamp.nullable(),
    latest_prediction: prediction.nullable(),
  })
  .strict();
const overview = z
  .object({
    total_users: count,
    active_users: count,
    inactive_users: count,
    admin_users: count,
    regular_users: count,
    total_buildings: count,
    total_measurements: count,
    total_predictions: count,
  })
  .strict();
function list<T extends z.ZodTypeAny>(schema: T) {
  return z
    .object({
      items: z.array(schema).max(200),
      total: count,
      limit: z.number().int().min(1).max(200),
      offset: count,
    })
    .strict();
}
export type AdminUser = z.infer<typeof user>;
export type AdminUserDetail = z.infer<typeof userDetail>;
export type AdminBuilding = z.infer<typeof building>;
export type AdminBuildingDetail = z.infer<typeof buildingDetail>;
export type AdminPrediction = z.infer<typeof prediction>;
export interface AdminPage {
  limit?: number;
  offset?: number;
}
export interface AdminUserFilters extends AdminPage {
  search?: string;
  role?: "USER" | "ADMIN";
  is_active?: boolean;
}
export interface AdminBuildingFilters extends AdminPage {
  search?: string;
  owner_id?: number;
  building_type?: string;
}
function positive(value: number) {
  if (!Number.isSafeInteger(value) || value < 1) throw new TypeError("Invalid admin ID");
  return value;
}
export function adminParams(filters: AdminPage & Record<string, unknown> = {}) {
  const params = new URLSearchParams();
  const limit = filters.limit ?? 50,
    offset = filters.offset ?? 0;
  if (
    !Number.isSafeInteger(limit) ||
    limit < 1 ||
    limit > 200 ||
    !Number.isSafeInteger(offset) ||
    offset < 0
  )
    throw new TypeError("Invalid admin pagination");
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  for (const [key, value] of Object.entries(filters)) {
    if (key === "limit" || key === "offset" || value === undefined) continue;
    if (key === "owner_id") positive(Number(value));
    const normalized =
      typeof value === "string" ? value.trim().replace(/\s+/g, " ") : String(value);
    if (normalized !== "") params.set(key, normalized);
  }
  return params.toString();
}
async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  signal?: AbortSignal,
  options: RequestInit = {},
) {
  const value = await apiRequest<unknown>(path, {
    credentials: "include",
    ...(signal ? { signal } : {}),
    ...options,
  });
  const parsed = schema.safeParse(value);
  if (!parsed.success) throw new ApiError("Backend returned malformed administration data.", 200);
  return parsed.data;
}
export const getAdminOverview = (signal?: AbortSignal) =>
  request("/admin/overview", overview, signal);
export const getAdminUsers = (filters: AdminUserFilters = {}, signal?: AbortSignal) =>
  request("/admin/users?" + adminParams({ ...filters }), list(user), signal);
export const getAdminUser = (value: number, signal?: AbortSignal) =>
  request(`/admin/users/${positive(value)}`, userDetail, signal);
export function updateAdminUserStatus(value: number, is_active: boolean) {
  if (typeof is_active !== "boolean") throw new TypeError("Expected boolean status");
  return request(`/admin/users/${positive(value)}/status`, userDetail, undefined, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", "X-SmartEnergy-CSRF": "1" },
    body: JSON.stringify({ is_active }),
  });
}
export const getAdminBuildings = (filters: AdminBuildingFilters = {}, signal?: AbortSignal) =>
  request("/admin/buildings?" + adminParams({ ...filters }), list(building), signal);
export const getAdminBuilding = (value: number, signal?: AbortSignal) =>
  request(`/admin/buildings/${positive(value)}`, buildingDetail, signal);
export const getAdminPredictions = (filters: AdminPage = {}, signal?: AbortSignal) =>
  request("/admin/predictions?" + adminParams({ ...filters }), list(prediction), signal);
export const adminKeys = {
  root: (actor: number | undefined) => ["admin", actor] as const,
  overview: (actor: number | undefined) => ["admin", actor, "overview"] as const,
  users: (actor: number | undefined) => ["admin", actor, "users"] as const,
};
export async function invalidateAdminStatus(
  client: { invalidateQueries: (options: { queryKey: readonly unknown[] }) => Promise<unknown> },
  actor: number | undefined,
) {
  await Promise.all([
    client.invalidateQueries({ queryKey: adminKeys.overview(actor) }),
    client.invalidateQueries({ queryKey: adminKeys.users(actor) }),
  ]);
}
