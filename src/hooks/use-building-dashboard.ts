import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api/client";
import { getBuildingDashboardSummary, dashboardKeys } from "@/lib/api/dashboard";
export function useBuildingDashboard(id: number, limit: number) {
  const { user, ready, retry } = useAuth();
  const query = useQuery({
    queryKey: [...dashboardKeys.building(user?.id, id), limit],
    queryFn: ({ signal }) => getBuildingDashboardSummary(id, limit, signal),
    enabled: ready && !!user,
    retry: false,
    staleTime: 0,
  });
  useEffect(() => {
    if (query.error instanceof ApiError && query.error.status === 401) retry();
  }, [query.error, retry]);
  return query;
}
