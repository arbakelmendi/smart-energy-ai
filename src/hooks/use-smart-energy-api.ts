import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { forecast, forecastWithRecommendation, getHealth, getModelInfo, getRecommendationThresholds, getModelComparison, getFeatureImportance } from "@/lib/api/smartEnergyApi";

// SSR and the first hydration render both stay pending. Fetch only after browser mount.
function useBrowserReady() {
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  return ready;
}

export function useHealth() {
  const enabled = useBrowserReady();
  return useQuery({ queryKey: ["smart-energy-api", "health"], queryFn: ({ signal }) => getHealth(signal),
    enabled, retry: false, staleTime: 30_000 });
}

export function useModelInfo(enabled = true) {
  const ready = useBrowserReady();
  return useQuery({ queryKey: ["smart-energy-api", "model-info"], queryFn: ({ signal }) => getModelInfo(signal),
    enabled: ready && enabled, retry: false, staleTime: 60_000 });
}

export function useRecommendationThresholds() {
  const enabled = useBrowserReady();
  return useQuery({ queryKey: ["smart-energy-api", "thresholds"], queryFn: ({ signal }) => getRecommendationThresholds(signal),
    enabled, retry: false, staleTime: 60_000 });
}

// Mutations are explicit caller actions; never run during render or generate feature history.
export function useForecast() {
  return useMutation({ mutationFn: forecast, retry: false });
}
export function useForecastRecommendation() {
  return useMutation({ mutationFn: forecastWithRecommendation, retry: false });
}


export function useModelComparison() {
  const enabled = useBrowserReady();
  return useQuery({ queryKey: ["smart-energy-api", "model-comparison"], queryFn: ({ signal }) => getModelComparison(signal),
    enabled, retry: false, staleTime: 60_000 });
}
export function useFeatureImportance() {
  const enabled = useBrowserReady();
  return useQuery({ queryKey: ["smart-energy-api", "feature-importance"], queryFn: ({ signal }) => getFeatureImportance(signal),
    enabled, retry: false, staleTime: 60_000 });
}
