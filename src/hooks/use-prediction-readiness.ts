import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api/client";
import { getPredictionReadiness, readinessKeys } from "@/lib/api/prediction-readiness";
export function usePredictionReadiness(buildingId: number) {
  const { user, ready, retry } = useAuth();
  const query = useQuery({
    queryKey: readinessKeys.building(user?.id, buildingId),
    queryFn: ({ signal }) => getPredictionReadiness(buildingId, signal),
    enabled: ready && !!user,
    retry: false,
    staleTime: 0,
  });
  useEffect(() => {
    if (query.error instanceof ApiError && query.error.status === 401) retry();
  }, [query.error, retry]);
  return query;
}
