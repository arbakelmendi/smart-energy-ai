import { createFileRoute, Link } from "@tanstack/react-router";
import { Building2, Plus } from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { Panel } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import { Sparkline } from "@/components/energy-wave";
import { buildTrend, buildings } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/buildings/")({
  head: () => ({
    meta: [
      { title: "Buildings — Smart Energy AI" },
      {
        name: "description",
        content: "Manage your building portfolio: current load, status, sensors and savings per site.",
      },
      { property: "og:title", content: "Buildings — Smart Energy AI" },
      { property: "og:description", content: "Portfolio of monitored buildings and their status." },
    ],
  }),
  component: BuildingsPage,
});

function BuildingsPage() {
  return (
    <AppShell
      title="Buildings"
      subtitle={`${buildings.length} sites monitored · 343 sensors online`}
      actions={
        <Button size="sm" variant="energy" onClick={() => toast.success("Building draft created — complete setup in onboarding.")}>
          <Plus className="size-3.5" /> Add building
        </Button>
      }
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {buildings.map((b, i) => {
          const spark = buildTrend(14, b.currentKwh / 800, 5 + i).map((t) => t.actual);
          return (
            <Link
              key={b.id}
              to="/buildings/$id"
              params={{ id: b.id }}
              className="panel lift block p-5"
            >
              <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
                <div className="min-w-0">
                  <p className="truncate text-base font-semibold">{b.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {b.type} · {b.areaM2.toLocaleString("en-US")} m² · {b.occupants} occupants
                  </p>
                </div>
                <span
                  className={cn(
                    "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                    b.status === "peak"
                      ? "bg-peak/15 text-peak"
                      : b.status === "watch"
                        ? "bg-muted text-muted-foreground"
                        : "bg-efficiency/15 text-efficiency",
                  )}
                >
                  {b.status}
                </span>
              </div>
              <p className="stat-number mt-4 text-2xl font-semibold">
                {b.currentKwh} <span className="text-sm font-normal text-muted-foreground">kWh/day</span>
              </p>
              <p className="mt-0.5 text-xs text-efficiency">−{b.savingsPct}% vs baseline</p>
              <Sparkline points={spark} tone={b.status === "peak" ? "peak" : "efficiency"} className="mt-4 h-12 w-full" />
              <p className="mt-3 flex items-center gap-1.5 font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
                <Building2 className="size-3" /> {b.sensors} sensors · {b.address}
              </p>
            </Link>
          );
        })}
        <Panel className="grid place-items-center border-dashed">
          <button
            className="p-8 text-center text-sm text-muted-foreground hover:text-efficiency"
            onClick={() => toast.success("Building draft created.")}
          >
            <Plus className="mx-auto size-6" />
            <span className="mt-2 block">Add another building</span>
          </button>
        </Panel>
      </div>
    </AppShell>
  );
}
