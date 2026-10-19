import { createFileRoute, Link } from "@tanstack/react-router";
import { Activity, Building2, Database, Users } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Panel, StatCard } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import { auditLog, platformStats } from "@/lib/mock-data";

export const Route = createFileRoute("/admin/")({
  head: () => ({ meta: [{ title: "Operational service not connected | SmartEnergyAI" }, { name: "description", content: "No verified operational data or management service is connected to this prototype." }] }),
  component: AdminOverview,
});

function AdminOverview() {
  return (
    <AppShell
      title="Admin overview"
      subtitle="Platform-wide statistics and activity"
      actions={
        <>
          <Button asChild size="sm" variant="wire">
            <Link to="/admin/users">Manage users</Link>
          </Button>
          <Button asChild size="sm" variant="ghost">
            <Link to="/admin/buildings">All buildings</Link>
          </Button>
        </>
      }
    >
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Registered users" value={platformStats.users} unit="accounts" icon={<Users className="size-4" />} />
          <StatCard label="Buildings" value={platformStats.buildings} unit="sites" icon={<Building2 className="size-4" />} tone="info" />
          <StatCard label="Energy monitored" value={platformStats.aggregatedGwh} decimals={1} unit="GWh/yr" icon={<Activity className="size-4" />} />
          <StatCard label="Mean accuracy" value={platformStats.avgAccuracy} decimals={1} unit="%" icon={<Database className="size-4" />} tone="info" />
        </div>

        <Panel title="Audit log" subtitle="most recent platform events" bodyClassName="p-0">
          <ul className="divide-y divide-border">
            {auditLog.map((e) => (
              <li key={e.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3 px-5 py-3.5">
                <div className="min-w-0">
                  <p className="text-sm font-medium">{e.action}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {e.target} · by {e.actor}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <span className="rounded-full border border-border px-2 py-0.5 font-mono text-[10px] uppercase">
                    {e.kind}
                  </span>
                  <p className="mt-1 font-mono text-[10px] text-muted-foreground">{e.at}</p>
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </AppShell>
  );
}
