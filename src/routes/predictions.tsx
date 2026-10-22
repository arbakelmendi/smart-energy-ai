import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { buildingSearch } from "@/lib/dashboard-view";
import { BuildingHistoryExplorer } from "@/components/building-history-explorer";
export const Route = createFileRoute("/predictions")({
  validateSearch: buildingSearch,
  head: () => ({ meta: [{ title: "Prediction history | SmartEnergyAI" }] }),
  component: Page,
});
function Page() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  return (
    <AppShell
      title="Prediction history"
      subtitle="Your persisted building data | manually entered or CSV imported"
    >
      <div className="space-y-6">
        <BuildingHistoryExplorer
          selected={search.building}
          onSelect={(id) => {
            void navigate({ search: { building: id } });
          }}
          mode="predictions"
        />
      </div>
    </AppShell>
  );
}
