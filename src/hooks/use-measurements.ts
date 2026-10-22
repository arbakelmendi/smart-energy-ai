import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api/client";
import {
  getMeasurements,
  createMeasurement,
  deleteMeasurement,
  importMeasurementsCsv,
  type CreateMeasurementRequest,
} from "@/lib/api/measurements";
export const measurementKeys = {
  building: (userId: number | undefined, buildingId: number) =>
    ["measurements", userId, buildingId] as const,
};
export function useMeasurements(buildingId: number, limit: number, offset: number) {
  const { user, ready, retry } = useAuth();
  const query = useQuery({
    queryKey: [...measurementKeys.building(user?.id, buildingId), limit, offset],
    queryFn: ({ signal }) => getMeasurements(buildingId, { limit, offset }, signal),
    enabled: ready && !!user,
    retry: false,
    staleTime: 0,
  });
  useEffect(() => {
    if (query.error instanceof ApiError && query.error.status === 401) retry();
  }, [query.error, retry]);
  return query;
}
function useMeasurementMutation<T>(buildingId: number, mutationFn: (body: T) => Promise<unknown>) {
  const { user, retry } = useAuth();
  const client = useQueryClient();
  return useMutation({
    mutationFn,
    retry: false,
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: measurementKeys.building(user?.id, buildingId) });
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 401) retry();
    },
  });
}
export function useCreateMeasurement(id: number) {
  return useMeasurementMutation(id, (body: CreateMeasurementRequest) =>
    createMeasurement(id, body),
  );
}
export function useDeleteMeasurement(id: number) {
  return useMeasurementMutation(id, (measurementId: number) =>
    deleteMeasurement(id, measurementId),
  );
}
export function useImportMeasurements(id: number) {
  const { user, retry } = useAuth();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => importMeasurementsCsv(id, file),
    retry: false,
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: measurementKeys.building(user?.id, id) });
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 401) retry();
    },
  });
}
