import { z } from "zod";
import { ApiError, apiRequest } from "./client.ts";

export const buildingTypes = ["Residential", "Office", "Educational", "Healthcare", "Retail", "Industrial", "Other"] as const;
export const buildingSchema = z.object({
  id: z.number().int().positive().safe(), name: z.string().min(1).max(200),
  building_type: z.enum(buildingTypes).nullable(), floor_area_m2: z.number().finite().positive().nullable(),
  city: z.string().max(200).nullable(), description: z.string().max(4000).nullable(),
  created_at: z.string().datetime({ local: true, offset: true }), updated_at: z.string().datetime({ local: true, offset: true }),
}).strict();
const listSchema = z.object({ buildings: z.array(buildingSchema) }).strict();
export type Building = z.infer<typeof buildingSchema>;
export interface CreateBuildingRequest {
  name: string; building_type?: typeof buildingTypes[number] | null;
  floor_area_m2?: number | null; city?: string | null; description?: string | null;
}
export type UpdateBuildingRequest = Partial<CreateBuildingRequest>;

export function parseBuildingId(value: string): number | null {
  const id = Number(value);
  return /^[0-9]+$/.test(value) && Number.isSafeInteger(id) && id > 0 ? id : null;
}
function path(id: number) {
  if (!Number.isSafeInteger(id) || id <= 0) throw new TypeError("Invalid building id");
  return `/buildings/${id}`;
}
function mutation(method: string, body?: CreateBuildingRequest | UpdateBuildingRequest): RequestInit {
  if (body?.floor_area_m2 != null && (typeof body.floor_area_m2 !== "number" || !Number.isFinite(body.floor_area_m2))) throw new TypeError("Floor area must be a finite number");
  return { method, credentials: "include", headers: { "Content-Type": "application/json", "X-SmartEnergy-CSRF": "1" }, ...(body ? { body: JSON.stringify(body) } : {}) };
}
function checked<T>(schema: z.ZodType<T>, payload: unknown): T {
  const value = schema.safeParse(payload);
  if (!value.success) throw new ApiError("Backend returned malformed building data.", 200);
  return value.data;
}
export async function getBuildings(signal?: AbortSignal) {
  return checked(listSchema, await apiRequest<unknown>("/buildings", { credentials: "include", ...(signal ? { signal } : {}) }));
}
export async function getBuilding(id: number, signal?: AbortSignal) {
  return checked(buildingSchema, await apiRequest<unknown>(path(id), { credentials: "include", ...(signal ? { signal } : {}) }));
}
export async function createBuilding(body: CreateBuildingRequest) {
  return checked(buildingSchema, await apiRequest<unknown>("/buildings", mutation("POST", body)));
}
export async function updateBuilding(id: number, body: UpdateBuildingRequest) {
  return checked(buildingSchema, await apiRequest<unknown>(path(id), mutation("PATCH", body)));
}
export async function deleteBuilding(id: number) { await apiRequest<void>(path(id), mutation("DELETE")); }
