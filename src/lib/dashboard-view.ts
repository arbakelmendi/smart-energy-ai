import type { Building } from "./api/buildings.ts";
import { parseBuildingId } from "./api/buildings.ts";
export function buildingSearch(search: Record<string, unknown>): { building?: string } {
  const value = search["building"];
  if (value === undefined) return {};
  return {
    building: typeof value === "string" || typeof value === "number" ? String(value) : "invalid",
  };
}
export function selectedOwnedBuilding(buildings: Building[], selected: string | undefined) {
  if (selected === undefined) return buildings[0] ?? null;
  const id = parseBuildingId(selected);
  return buildings.find((b) => b.id === id) ?? null;
}
/** Wall-clock axis coordinates only; no timezone is assigned to naive observations. */
export function energyChartPoints(points: { timestamp: string; Appliances: number }[]) {
  return points.map((point) => ({ ...point, x: Date.parse(point.timestamp + "Z") }));
}
export function localAxisLabel(value: number) {
  return new Date(value).toISOString().slice(0, 16).replace("T", " ");
}
