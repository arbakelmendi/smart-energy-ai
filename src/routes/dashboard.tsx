import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { ModelPerformance, ValidationComparison, FeatureImportance, RecommendationBands, LiveDataState } from "@/components/research-dashboard";

export const Route = createFileRoute("/dashboard")({
  head: () => ({ meta: [{ title: "Research dashboard | SmartEnergyAI" },
    { name: "description", content: "Verified research results and forecast-based decision support. Live sensor history is not connected." }] }),
  component: DashboardPage,
});

function DashboardPage() {
  return <AppShell title="Research dashboard" subtitle="Verified research prototype | operational feed not connected">
    <div className="space-y-6"><ModelPerformance /><div className="grid min-w-0 gap-4 xl:grid-cols-2"><ValidationComparison /><FeatureImportance /></div><RecommendationBands /><LiveDataState /></div>
  </AppShell>;
}
