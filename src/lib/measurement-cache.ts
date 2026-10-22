import { dashboardKeys } from "./api/dashboard.ts";
import type { QueryClient } from "@tanstack/react-query";
import { predictionKeys } from "./api/building-predictions.ts";
import { readinessKeys } from "./api/prediction-readiness.ts";
export const measurementKeys = {
  building: (userId: number | undefined, buildingId: number) =>
    ["measurements", userId, buildingId] as const,
};
export async function invalidateMeasurementDependents(
  client: QueryClient,
  userId: number | undefined,
  buildingId: number,
) {
  // Invalidate every history page and its authoritative compatibility assessment.
  await Promise.all([
    client.invalidateQueries({ queryKey: dashboardKeys.building(userId, buildingId) }),
    client.invalidateQueries({ queryKey: measurementKeys.building(userId, buildingId) }),
    client.invalidateQueries({ queryKey: readinessKeys.building(userId, buildingId) }),
    client.invalidateQueries({ queryKey: predictionKeys.building(userId, buildingId) }),
  ]);
}
