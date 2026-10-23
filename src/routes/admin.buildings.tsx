import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { AdminBuildings } from "@/components/admin-buildings";
import { adminSelection } from "@/lib/admin-view";
export const Route = createFileRoute("/admin/buildings")({
  validateSearch: adminSelection,
  head: () => ({ meta: [{ title: "All buildings | SmartEnergyAI" }] }),
  component: Page,
});
function Page() {
  const search = Route.useSearch();
  return (
    <AppShell title="All buildings" subtitle="Read-only inventory across owners">
      <AdminBuildings selected={search.building} />
    </AppShell>
  );
}
