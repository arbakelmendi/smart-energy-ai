import { z } from "zod";
import { ApiError, apiRequest } from "./client.ts";

export const rawFields = [
  "Appliances",
  "lights",
  "T1",
  "RH_1",
  "T2",
  "RH_2",
  "T3",
  "RH_3",
  "T4",
  "RH_4",
  "T5",
  "RH_5",
  "T6",
  "RH_6",
  "T7",
  "RH_7",
  "T8",
  "RH_8",
  "T9",
  "RH_9",
  "T_out",
  "Press_mm_hg",
  "RH_out",
  "Windspeed",
  "Visibility",
  "Tdewpoint",
] as const;
export type RawField = (typeof rawFields)[number];
const numericShape = Object.fromEntries(
  rawFields.map((field) => [field, z.number().finite()]),
) as Record<RawField, z.ZodNumber>;
const timestamp = z
  .string()
  .datetime({ local: true })
  .refine((value) => !/[Zz]|[+-][0-9]{2}:[0-9]{2}$/.test(value), "Use local time without timezone");
export const createMeasurementSchema = z.object({ timestamp, ...numericShape }).strict();
export const measurementSchema = createMeasurementSchema.extend({
  id: z.number().int().positive().safe(),
  building_id: z.number().int().positive().safe(),
});
const listSchema = z
  .object({
    items: z.array(measurementSchema),
    total: z.number().int().nonnegative(),
    limit: z.number().int().positive().max(500),
    offset: z.number().int().nonnegative(),
    first_timestamp: timestamp.nullable(),
    last_timestamp: timestamp.nullable(),
  })
  .strict();
const importSchema = z
  .object({
    building_id: z.number().int().positive().safe(),
    rows_received: z.number().int().positive(),
    rows_imported: z.number().int().positive(),
    first_timestamp: timestamp,
    last_timestamp: timestamp,
    ignored_columns: z.array(z.enum(["rv1", "rv2"])),
  })
  .strict();
export type Measurement = z.infer<typeof measurementSchema>;
export type CreateMeasurementRequest = z.infer<typeof createMeasurementSchema>;
export type MeasurementListResponse = z.infer<typeof listSchema>;
export type MeasurementImportResponse = z.infer<typeof importSchema>;
export function fieldUnit(field: RawField) {
  if (field === "Appliances" || field === "lights") return "Wh";
  if (field.startsWith("RH")) return "%";
  if (field.startsWith("T")) return "°C";
  return ({ Press_mm_hg: "mm Hg", Windspeed: "m/s", Visibility: "km" } as Record<string, string>)[
    field
  ];
}
function path(buildingId: number) {
  if (!Number.isSafeInteger(buildingId) || buildingId < 1)
    throw new TypeError("Invalid building id");
  return `/buildings/${buildingId}/measurements`;
}
function checked<T>(schema: z.ZodType<T>, payload: unknown): T {
  const parsed = schema.safeParse(payload);
  if (!parsed.success) throw new ApiError("Backend returned malformed measurement data.", 200);
  return parsed.data;
}
const headers = { "X-SmartEnergy-CSRF": "1" };
export async function getMeasurements(
  buildingId: number,
  pagination = { limit: 100, offset: 0 },
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
  return checked(
    listSchema,
    await apiRequest<unknown>(
      `${path(buildingId)}?limit=${pagination.limit}&offset=${pagination.offset}`,
      { credentials: "include", ...(signal ? { signal } : {}) },
    ),
  );
}
export async function createMeasurement(buildingId: number, body: CreateMeasurementRequest) {
  const parsed = createMeasurementSchema.parse(body);
  return checked(
    measurementSchema,
    await apiRequest<unknown>(path(buildingId), {
      method: "POST",
      credentials: "include",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(parsed),
    }),
  );
}
export async function deleteMeasurement(buildingId: number, measurementId: number) {
  if (!Number.isSafeInteger(measurementId) || measurementId < 1)
    throw new TypeError("Invalid measurement id");
  await apiRequest<void>(`${path(buildingId)}/${measurementId}`, {
    method: "DELETE",
    credentials: "include",
    headers,
  });
}
export async function importMeasurementsCsv(buildingId: number, file: File) {
  const body = new FormData();
  body.append("file", file);
  // Browser owns multipart boundary. Longer bounded timeout supports the full local UCI file.
  return checked(
    importSchema,
    await apiRequest<unknown>(`${path(buildingId)}/import`, {
      method: "POST",
      credentials: "include",
      headers,
      body,
      signal: AbortSignal.timeout(120_000),
    }),
  );
}
