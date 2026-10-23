import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { AdminUsers } from "@/components/admin-users";
import { adminSelection } from "@/lib/admin-view";
export const Route = createFileRoute("/admin/users")({
  validateSearch: adminSelection,
  head: () => ({ meta: [{ title: "User management | SmartEnergyAI" }] }),
  component: Page,
});
function Page() {
  const search = Route.useSearch();
  return (
    <AppShell
      title="User management"
      subtitle="Safe account oversight and session-revoking status changes"
    >
      <AdminUsers selected={search.user} />
    </AppShell>
  );
}
