import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { AlertTriangle, ArrowUpRight, Gauge, Info, Leaf, Zap } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { StatCard, Panel, MetricPill } from "@/components/ui-kit";
import { ActualVsPredictedChart, TrendAreaChart, CompareBarChart } from "@/components/charts";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  alerts,
  buildTrend,
  buildings,
  hourlyProfile,
  models,
  recommendations,
  weekdayProfile,
} from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — Smart Energy AI" },
      {
        name: "description",
        content:
          "Live consumption vs forecast, estimated savings, anomaly alerts and active AI recommendations across your building portfolio.",
      },
      { property: "og:title", content: "Dashboard — Smart Energy AI" },
      { property: "og:description", content: "Live consumption vs forecast and savings tracking." },
    ],
  }),
  component: DashboardPage,
});

const ranges = { "7": 7, "30": 30, "90": 90 } as const;

function DashboardPage() {
  const [range, setRange] = useState<keyof typeof ranges>("30");
  const [buildingId, setBuildingId] = useState("all");

  const scale =
    buildingId === "all" ? 1 : (buildings.find((b) => b.id === buildingId)?.currentKwh ?? 800) / 800;
  const trend = buildTrend(ranges[range], scale, buildingId === "all" ? 3 : 7);
  const totalActual = trend.reduce((s, d) => s + d.actual, 0);
  const totalPredicted = trend.reduce((s, d) => s + d.predicted, 0);
  const active = recommendations.filter((r) => r.status !== "dismissed").slice(0, 3);

  return (
    <AppShell
      title="Portfolio overview"
      subtitle="Aggregated telemetry · 15-minute resolution · updated 09:45"
      actions={
        <>
          <Select value={buildingId} onValueChange={setBuildingId}>
            <SelectTrigger className="h-8 w-[230px] text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All buildings (5)</SelectItem>
              {buildings.map((b) => (
                <SelectItem key={b.id} value={b.id}>
                  {b.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Tabs value={range} onValueChange={(v) => setRange(v as keyof typeof ranges)}>
            <TabsList className="h-8">
              <TabsTrigger value="7" className="text-xs">7 days</TabsTrigger>
              <TabsTrigger value="30" className="text-xs">30 days</TabsTrigger>
              <TabsTrigger value="90" className="text-xs">90 days</TabsTrigger>
            </TabsList>
          </Tabs>
          <Button asChild size="sm" variant="wire" className="ml-auto">
            <Link to="/predictions">
              Forecast detail <ArrowUpRight className="size-3.5" />
            </Link>
          </Button>
        </>
      }
    >
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Current load"
            value={trend.at(-1)?.actual ?? 0}
            decimals={1}
            unit="kWh/day"
            delta={`${((1 - totalActual / totalPredicted) * 100).toFixed(1)}% vs forecast`}
            icon={<Zap className="size-4" />}
            spark={trend.slice(-14).map((t) => t.actual)}
          />
          <StatCard
            label="Estimated savings"
            value={(totalPredicted - totalActual) * 0.132}
            decimals={0}
            unit="€"
            delta={`${Math.round(totalPredicted - totalActual)} kWh avoided`}
            icon={<Leaf className="size-4" />}
            spark={trend.slice(-14).map((t) => t.predicted - t.actual)}
          />
          <StatCard
            label="Peak demand"
            value={Math.max(...trend.map((t) => t.actual))}
            decimals={1}
            unit="kWh"
            tone="peak"
            delta="peak window 17:00–19:00"
            icon={<Gauge className="size-4" />}
            spark={hourlyProfile.map((h) => h.kwh)}
          />
          <StatCard
            label="Model accuracy"
            value={models[0]!.r2 * 100}
            decimals={1}
            unit="% R²"
            tone="info"
            delta={`MAE ${models[0]!.mae} kWh · retrained 02:10`}
            icon={<Info className="size-4" />}
          />
        </div>

        <Panel
          title="Actual vs predicted consumption"
          subtitle="with 95% confidence interval"
          action={
            <div className="hidden gap-2 sm:flex">
              <MetricPill label="MAE" value={`${models[0]!.mae}`} />
              <MetricPill label="RMSE" value={`${models[0]!.rmse}`} />
            </div>
          }
        >
          <ActualVsPredictedChart data={trend} height={340} />
        </Panel>

        <div className="grid gap-4 lg:grid-cols-[1.25fr_1fr]">
          <Panel title="Active AI recommendations" subtitle={`${active.length} awaiting action`}>
            <ul className="space-y-3">
              {active.map((r) => (
                <li key={r.id} className="rounded-xl border border-border bg-surface-2/50 p-4 lift">
                  <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
                    <p className="min-w-0 text-sm font-medium">{r.title}</p>
                    <span
                      className={cn(
                        "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                        r.impact === "high"
                          ? "bg-efficiency/15 text-efficiency"
                          : r.impact === "medium"
                            ? "bg-peak/15 text-peak"
                            : "bg-muted text-muted-foreground",
                      )}
                    >
                      {r.impact}
                    </span>
                  </div>
                  <p className="mt-1.5 text-xs text-muted-foreground">{r.detail}</p>
                  <p className="mt-2 font-mono text-[11px] text-efficiency">
                    −{r.savingKwh} kWh/week · €{r.savingEur.toFixed(2)}/day saved
                  </p>
                </li>
              ))}
            </ul>
            <Button asChild variant="wire" size="sm" className="mt-4 w-full">
              <Link to="/recommendations">See all recommendations</Link>
            </Button>
          </Panel>

          <div id="alerts" className="space-y-4">
            <Panel title="Anomaly alerts" subtitle="detected outside forecast band">
              <ul className="space-y-3">
                {alerts.map((a) => (
                  <li key={a.id} className="flex items-start gap-3">
                    <AlertTriangle
                      className={cn(
                        "mt-0.5 size-4 shrink-0",
                        a.severity === "critical"
                          ? "text-destructive"
                          : a.severity === "warning"
                            ? "text-peak"
                            : "text-muted-foreground",
                      )}
                    />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{a.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {a.building} · {a.delta} · {a.time}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </Panel>
            <Panel title="Weekday profile" subtitle="actual vs forecast, kWh">
              <CompareBarChart
                data={weekdayProfile}
                xKey="day"
                height={200}
                highlightMax
                bars={[
                  { key: "kwh", name: "Actual", tone: "chart-1" },
                  { key: "forecast", name: "Forecast", tone: "chart-3" },
                ]}
              />
            </Panel>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <Panel title="Daily load curve" className="lg:col-span-2">
            <TrendAreaChart data={hourlyProfile} xKey="hour" dataKey="kwh" height={220} />
          </Panel>
          <Panel title="Buildings" subtitle="current load and status">
            <ul className="space-y-2.5">
              {buildings.map((b) => (
                <li key={b.id}>
                  <Link
                    to="/buildings/$id"
                    params={{ id: b.id }}
                    className="flex items-center justify-between gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-muted"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm">{b.name}</span>
                      <span className="text-[11px] text-muted-foreground">{b.type}</span>
                    </span>
                    <span className="shrink-0 text-right">
                      <span className="stat-number block text-sm">{b.currentKwh} kWh</span>
                      <span
                        className={cn(
                          "text-[10px] uppercase",
                          b.status === "peak"
                            ? "text-peak"
                            : b.status === "watch"
                              ? "text-muted-foreground"
                              : "text-efficiency",
                        )}
                      >
                        {b.status}
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      </div>
    </AppShell>
  );
}
