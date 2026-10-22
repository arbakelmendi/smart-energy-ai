import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { buildingSearch } from "@/lib/dashboard-view";
import { UserDashboard } from "@/components/user-dashboard";
import { ResearchInformation } from "@/components/research-information";
export const Route = createFileRoute("/dashboard")({
  validateSearch: buildingSearch,
  head: () => ({ meta: [{ title: "Your building dashboard | SmartEnergyAI" }] }),
  component: Page,
});
function Page() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  return (
    <AppShell
      title="Your building dashboard"
      subtitle="Your persisted building data | manually entered or CSV imported"
    >
      <div className="space-y-6">
        <UserDashboard
          selected={search.building}
          onSelect={(id) => {
            void navigate({ search: { building: id } });
          }}
        />
        <ResearchInformation />
      </div>
    </AppShell>
  );
}
