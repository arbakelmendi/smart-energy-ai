import { dashboardKeys } from "@/lib/api/dashboard";
import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api/client";
import {
  createBuildingPrediction,
  getBuildingPredictions,
  predictionKeys,
} from "@/lib/api/building-predictions";
import { readinessKeys } from "@/lib/api/prediction-readiness";
export function useBuildingPredictions(id: number, limit: number, offset: number) {
  const { user, ready, retry } = useAuth();
  const query = useQuery({
    queryKey: [...predictionKeys.building(user?.id, id), limit, offset],
    queryFn: ({ signal }) => getBuildingPredictions(id, { limit, offset }, signal),
    enabled: ready && !!user,
    retry: false,
    staleTime: 0,
  });
  useEffect(() => {
    if (query.error instanceof ApiError && query.error.status === 401) retry();
  }, [query.error, retry]);
  return query;
}
export function useCreateBuildingPrediction(id: number) {
  const { user, retry } = useAuth();
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => createBuildingPrediction(id),
    retry: false,
    onSuccess: async () => {
      await Promise.all([client.invalidateQueries({ queryKey: predictionKeys.building(user?.id, id) }),client.invalidateQueries({ queryKey: dashboardKeys.building(user?.id, id) })]);
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 401) retry();
      if (error instanceof ApiError && error.status === 409)
        void Promise.all([client.invalidateQueries({ queryKey: readinessKeys.building(user?.id,id) }),client.invalidateQueries({ queryKey: dashboardKeys.building(user?.id,id) })]);
    },
  });
}
