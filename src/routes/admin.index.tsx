import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { AdminOverview } from "@/components/admin-overview";
export const Route = createFileRoute("/admin/")({
  head: () => ({ meta: [{ title: "Admin overview | SmartEnergyAI" }] }),
  component: Page,
});
function Page() {
  return (
    <AppShell
      title="Admin overview"
      subtitle="Application-wide persisted counts and prediction history"
    >
      <AdminOverview />
    </AppShell>
  );
}
