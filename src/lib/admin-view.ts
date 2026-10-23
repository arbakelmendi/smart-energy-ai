import { parseBuildingId } from "./api/buildings.ts";
export function adminSelection(search: Record<string, unknown>): {
  user?: string;
  building?: string;
} {
  const result: { user?: string; building?: string } = {};
  for (const key of ["user", "building"] as const) {
    const value = search[key];
    if (value !== undefined)
      result[key] =
        typeof value === "string" || typeof value === "number" ? String(value) : "invalid";
  }
  return result;
}
export const adminSelectedId = (value: string | undefined) =>
  value === undefined ? null : parseBuildingId(value);
export const deactivationWarning =
  "Deactivating this account will prevent login and invalidate active sessions. Stored buildings, measurements and predictions will be retained.";
export function statusActionAllowed(actor: number, target: number, active: boolean) {
  return !(actor === target && active);
}
