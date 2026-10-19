import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { Panel, StatCard, MetricPill } from "@/components/ui-kit";
import { ActualVsPredictedChart, CompareBarChart, TrendAreaChart } from "@/components/charts";
import { Button } from "@/components/ui/button";
import {
  alerts,
  buildTrend,
  getBuilding,
  hourlyProfile,
  models,
  recommendations,
  weekdayProfile,
} from "@/lib/mock-data";

export const Route = createFileRoute("/buildings/$id")({
  loader: ({ params }) => {
    const building = getBuilding(params.id);
    if (!building) throw notFound();
    return { building };
  },
  head: () => ({ meta: [{ title: "Building service not connected | SmartEnergyAI" }, { name: "description", content: "No verified operational building service is connected to this prototype." }] }),
  component: BuildingDetail,
});

function BuildingDetail() {
  const { building } = Route.useLoaderData();
  const scale = building.currentKwh / 800;
  const trend = buildTrend(30, scale, 5);
  const recs = recommendations.filter((r) => r.buildingId === building.id);
  const buildingAlerts = alerts.filter((a) => a.building === building.name);

  return (
    <AppShell
      title={building.name}
      subtitle={`${building.type} · ${building.areaM2.toLocaleString("en-US")} m² · ${building.address}`}
      actions={
        <>
          <Button asChild size="sm" variant="ghost">
            <Link to="/buildings">← All buildings</Link>
          </Button>
          <Button size="sm" variant="wire" onClick={() => toast.success("Building metadata saved.")}>
            <Pencil className="size-3.5" /> Edit
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-destructive"
            onClick={() => toast.error("Deleting a building is disabled in demo mode.")}
          >
            <Trash2 className="size-3.5" /> Delete
          </Button>
        </>
      }
    >
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Current load" value={building.currentKwh} decimals={1} unit="kWh/day" spark={trend.slice(-14).map((t) => t.actual)} />
          <StatCard label="Baseline" value={building.baselineKwh} decimals={1} unit="kWh/day" tone="peak" />
          <StatCard label="Reduction" value={building.savingsPct} decimals={1} unit="%" delta="vs pre-AI baseline" />
          <StatCard label="Sensors online" value={building.sensors} unit="devices" tone="info" />
        </div>

        <Panel title="Actual vs predicted" subtitle="30 days · 95% confidence interval">
          <ActualVsPredictedChart data={trend} height={320} />
        </Panel>

        <div className="grid gap-4 lg:grid-cols-3">
          <Panel title="Daily load curve" className="lg:col-span-2">
            <TrendAreaChart
              data={hourlyProfile.map((h) => ({ hour: h.hour, kwh: Math.round(h.kwh * scale * 10) / 10 }))}
              xKey="hour"
              dataKey="kwh"
              height={220}
            />
          </Panel>
          <div className="space-y-3">
            <MetricPill label="MAE" value={`${models[0]!.mae} kWh`} />
            <MetricPill label="RMSE" value={`${models[0]!.rmse} kWh`} />
            <MetricPill label="R²" value={models[0]!.r2.toFixed(3)} />
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Panel title="Weekday profile">
            <CompareBarChart
              data={weekdayProfile.map((w) => ({ day: w.day, kwh: Math.round(w.kwh * scale * 10) / 10 }))}
              xKey="day"
              height={220}
              highlightMax
              bars={[{ key: "kwh", name: "Actual", tone: "chart-1" }]}
            />
          </Panel>
          <Panel title="Open items" subtitle={`${recs.length} recommendations · ${buildingAlerts.length} alerts`}>
            <ul className="space-y-3 text-sm">
              {recs.map((r) => (
                <li key={r.id} className="rounded-xl border border-border bg-surface-2/50 p-3">
                  <p className="font-medium">{r.title}</p>
                  <p className="mt-1 font-mono text-[11px] text-efficiency">
                    −{r.savingKwh} kWh/week · {r.status.replace("_", " ")}
                  </p>
                </li>
              ))}
              {buildingAlerts.map((a) => (
                <li key={a.id} className="rounded-xl border border-peak/30 bg-peak/8 p-3">
                  <p className="font-medium">{a.title}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {a.delta} · {a.time}
                  </p>
                </li>
              ))}
              {recs.length === 0 && buildingAlerts.length === 0 ? (
                <li className="py-6 text-center text-muted-foreground">Nothing open for this site.</li>
              ) : null}
            </ul>
          </Panel>
        </div>
      </div>
    </AppShell>
  );
}
