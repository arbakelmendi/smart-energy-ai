import { measurementKeys } from "@/lib/measurement-cache";
import { readinessKeys } from "@/lib/api/prediction-readiness";
import { predictionKeys } from "@/lib/api/building-predictions";
import { dashboardKeys } from "@/lib/api/dashboard";
import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api/client";
import { createBuilding, deleteBuilding, getBuilding, getBuildings, updateBuilding, type UpdateBuildingRequest } from "@/lib/api/buildings";

export const buildingKeys = {
  list: (userId: number | undefined) => ["buildings", userId, "list"] as const,
  detail: (userId: number | undefined, id: number | null) => ["buildings", userId, "detail", id] as const,
};
function useRefreshUnauthorized(error: Error | null) {
  const { retry } = useAuth();
  useEffect(() => { if (error instanceof ApiError && error.status === 401) retry(); }, [error, retry]);
}
export function useBuildings() {
  const { user, ready } = useAuth();
  const query = useQuery({ queryKey: buildingKeys.list(user?.id), queryFn: ({ signal }) => getBuildings(signal),
    enabled: ready && !!user, retry: false, staleTime: 0 });
  useRefreshUnauthorized(query.error);
  return query;
}
export function useBuilding(id: number | null) {
  const { user, ready } = useAuth();
  const query = useQuery({ queryKey: buildingKeys.detail(user?.id, id), queryFn: ({ signal }) => getBuilding(id!, signal),
    enabled: ready && !!user && id !== null, retry: false, staleTime: 0 });
  useRefreshUnauthorized(query.error);
  return query;
}
export function useCreateBuilding() {
  const client = useQueryClient(); const { user, retry } = useAuth();
  return useMutation({ mutationFn: createBuilding, retry: false,
    onSuccess: async (building) => { client.setQueryData(buildingKeys.detail(user?.id, building.id), building); await client.invalidateQueries({ queryKey: buildingKeys.list(user?.id) }); },
    onError: (error) => { if (error instanceof ApiError && error.status === 401) retry(); },
  });
}
export function useUpdateBuilding(id: number) {
  const client = useQueryClient(); const { user, retry } = useAuth();
  return useMutation({ mutationFn: (body: UpdateBuildingRequest) => updateBuilding(id, body), retry: false,
    onSuccess: async (building) => { client.setQueryData(buildingKeys.detail(user?.id, id), building); await Promise.all([client.invalidateQueries({ queryKey: buildingKeys.list(user?.id) }),client.invalidateQueries({queryKey:dashboardKeys.building(user?.id,id)})]); },
    onError: (error) => { if (error instanceof ApiError && error.status === 401) retry(); },
  });
}
export function useDeleteBuilding(id: number) {
  const client = useQueryClient(); const { user, retry } = useAuth();
  return useMutation({ mutationFn: () => deleteBuilding(id), retry: false,
    onSuccess: async () => { const keys=[buildingKeys.detail(user?.id,id),dashboardKeys.building(user?.id,id),measurementKeys.building(user?.id,id),readinessKeys.building(user?.id,id),predictionKeys.building(user?.id,id)]; await Promise.all(keys.map(queryKey=>client.cancelQueries({queryKey}))); keys.forEach(queryKey=>client.removeQueries({queryKey})); await client.invalidateQueries({ queryKey: buildingKeys.list(user?.id) }); },
    onError: (error) => { if (error instanceof ApiError && error.status === 401) retry(); },
  });
}
