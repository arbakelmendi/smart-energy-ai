import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api/client";
import {
  adminKeys,
  getAdminOverview,
  getAdminUsers,
  getAdminUser,
  getAdminBuildings,
  getAdminBuilding,
  getAdminPredictions,
  updateAdminUserStatus,
  invalidateAdminStatus,
  type AdminUserFilters,
  type AdminBuildingFilters,
} from "@/lib/api/admin";
function useAdminQuery<T>(
  part: readonly unknown[],
  load: (signal: AbortSignal) => Promise<T>,
  valid = true,
) {
  const { user, ready, retry } = useAuth();
  const query = useQuery({
    queryKey: [...adminKeys.root(user?.id), ...part],
    queryFn: ({ signal }) => load(signal),
    enabled: ready && user?.role === "ADMIN" && valid,
    retry: false,
    staleTime: 0,
  });
  useEffect(() => {
    if (
      query.error instanceof ApiError &&
      (query.error.status === 401 || query.error.status === 403)
    )
      retry();
  }, [query.error, retry]);
  return query;
}
export const useAdminOverview = () => useAdminQuery(["overview"], getAdminOverview);
export const useAdminUsers = (filters: AdminUserFilters) =>
  useAdminQuery(["users", "list", filters], (signal) => getAdminUsers(filters, signal));
export const useAdminUser = (id: number | null) =>
  useAdminQuery(["users", "detail", id], (signal) => getAdminUser(id!, signal), id !== null);
export const useAdminBuildings = (filters: AdminBuildingFilters) =>
  useAdminQuery(["buildings", "list", filters], (signal) => getAdminBuildings(filters, signal));
export const useAdminBuilding = (id: number | null) =>
  useAdminQuery(
    ["buildings", "detail", id],
    (signal) => getAdminBuilding(id!, signal),
    id !== null,
  );
export const useAdminPredictions = (offset: number) =>
  useAdminQuery(["predictions", 50, offset], (signal) =>
    getAdminPredictions({ limit: 50, offset }, signal),
  );
export function useAdminUserStatus() {
  const client = useQueryClient();
  const { user, retry } = useAuth();
  return useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      updateAdminUserStatus(id, is_active),
    retry: false,
    onSuccess: () => invalidateAdminStatus(client, user?.id),
    onError: (error) => {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) retry();
    },
  });
}
