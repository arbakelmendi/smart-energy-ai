import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { ModelPerformance, ValidationComparison, FeatureImportance, RecommendationBands, LiveDataState } from "@/components/research-dashboard";

export const Route = createFileRoute("/predictions")({
  head: () => ({ meta: [{ title: "Model performance | SmartEnergyAI" },
    { name: "description", content: "Verified research results and forecast-based decision support. Live sensor history is not connected." }] }),
  component: PredictionsPage,
});

function PredictionsPage() {
  return <AppShell title="Model performance" subtitle="Verified research prototype | operational feed not connected">
    <div className="space-y-6"><ModelPerformance /><ValidationComparison /><FeatureImportance /><LiveDataState /></div>
  </AppShell>;
}
