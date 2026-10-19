import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { ModelPerformance, ValidationComparison, FeatureImportance, RecommendationBands, LiveDataState } from "@/components/research-dashboard";

export const Route = createFileRoute("/recommendations")({
  head: () => ({ meta: [{ title: "Decision support | SmartEnergyAI" },
    { name: "description", content: "Verified research results and forecast-based decision support. Live sensor history is not connected." }] }),
  component: RecommendationsPage,
});

function RecommendationsPage() {
  return <AppShell title="Decision support" subtitle="Verified research prototype | operational feed not connected">
    <div className="space-y-6"><LiveDataState /><RecommendationBands /></div>
  </AppShell>;
}
