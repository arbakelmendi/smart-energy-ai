import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Cpu, Thermometer } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Panel, MetricPill } from "@/components/ui-kit";
import { ActualVsPredictedChart, TrendAreaChart, WeightBars, CompareBarChart } from "@/components/charts";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { buildForecast, buildTrend, featureImportance, models, seasonProfile } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/predictions")({
  head: () => ({
    meta: [
      { title: "Predictions — Smart Energy AI" },
      {
        name: "description",
        content:
          "Short- and long-term consumption forecasts with MAE, RMSE and R² per algorithm, plus factor filters for temperature, humidity, season and time of day.",
      },
      { property: "og:title", content: "Predictions — Smart Energy AI" },
      { property: "og:description", content: "Forecast horizons and model benchmark comparison." },
    ],
  }),
  component: PredictionsPage,
});

const factors = [
  { key: "temperature", label: "Temperature", unit: " °C", tone: "chart-2" },
  { key: "humidity", label: "Humidity", unit: " %", tone: "chart-3" },
] as const;

function PredictionsPage() {
  const [horizon, setHorizon] = useState<"short" | "long">("short");
  const [factor, setFactor] = useState<(typeof factors)[number]["key"]>("temperature");

  const shortTerm = buildForecast(48);
  const longTerm = buildTrend(90, 1, 11);
  const data = horizon === "short" ? shortTerm : longTerm;
  const activeFactor = factors.find((f) => f.key === factor)!;

  return (
    <AppShell
      title="Forecasting"
      subtitle="Active model: LSTM seq-48 v4.2 · nightly retraining at 02:00"
      actions={
        <Tabs value={horizon} onValueChange={(v) => setHorizon(v as "short" | "long")}>
          <TabsList className="h-8">
            <TabsTrigger value="short" className="text-xs">Short term · 48 h</TabsTrigger>
            <TabsTrigger value="long" className="text-xs">Long term · 90 d</TabsTrigger>
          </TabsList>
        </Tabs>
      }
    >
      <div className="space-y-6">
        <Panel
          title={horizon === "short" ? "Next 48 hours (hourly)" : "Next 90 days (daily)"}
          subtitle="predicted load with 95% confidence interval; solid line is realised data"
        >
          <ActualVsPredictedChart data={data} height={360} />
        </Panel>

        <div className="grid gap-4 lg:grid-cols-4">
          <MetricPill label="MAE" value={`${models[0]!.mae} kWh`} hint="mean absolute error" />
          <MetricPill label="RMSE" value={`${models[0]!.rmse} kWh`} hint="root mean squared error" />
          <MetricPill label="R²" value={models[0]!.r2.toFixed(3)} hint="held-out test set" />
          <MetricPill label="MAPE" value="3.8 %" hint="mean abs. percentage error" />
        </div>

        <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
          <Panel
            title="Driving factors"
            subtitle="filter the forecast window by exogenous variable"
            action={
              <Tabs value={factor} onValueChange={(v) => setFactor(v as typeof factor)}>
                <TabsList className="h-8">
                  {factors.map((f) => (
                    <TabsTrigger key={f.key} value={f.key} className="text-xs">
                      {f.label}
                    </TabsTrigger>
                  ))}
                </TabsList>
              </Tabs>
            }
          >
            <TrendAreaChart
              data={data as unknown as Array<Record<string, unknown>>}
              dataKey={activeFactor.key}
              tone={activeFactor.tone}
              unit={activeFactor.unit}
              height={240}
            />
            <p className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
              <Thermometer className="size-3.5 text-efficiency" />
              Heating degree-day sensitivity: 18.4 kWh per °C below the 15.5 °C base temperature.
            </p>
          </Panel>
          <Panel title="Feature importance" subtitle="permutation importance">
            <WeightBars items={featureImportance} />
          </Panel>
        </div>

        <Panel title="Algorithm comparison" subtitle="identical splits, identical feature set" bodyClassName="p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="border-b border-border text-left">
                <tr className="font-mono text-[10px] tracking-[0.16em] text-muted-foreground uppercase">
                  <th className="px-5 py-3 font-medium">Algorithm</th>
                  <th className="px-5 py-3 font-medium">Family</th>
                  <th className="px-5 py-3 font-medium">MAE</th>
                  <th className="px-5 py-3 font-medium">RMSE</th>
                  <th className="px-5 py-3 font-medium">R²</th>
                  <th className="px-5 py-3 font-medium">Train</th>
                  <th className="px-5 py-3 font-medium">State</th>
                </tr>
              </thead>
              <tbody>
                {models.map((m) => (
                  <tr
                    key={m.name}
                    className={cn(
                      "border-b border-border/60 last:border-0",
                      m.active && "bg-efficiency/6",
                    )}
                  >
                    <td className="px-5 py-3.5 font-medium">{m.name}</td>
                    <td className="px-5 py-3.5 text-muted-foreground">{m.type}</td>
                    <td className="stat-number px-5 py-3.5">{m.mae}</td>
                    <td className="stat-number px-5 py-3.5">{m.rmse}</td>
                    <td className="stat-number px-5 py-3.5 text-efficiency">{m.r2.toFixed(3)}</td>
                    <td className="px-5 py-3.5 text-muted-foreground">{m.trainSec}s</td>
                    <td className="px-5 py-3.5">
                      {m.active ? (
                        <Badge className="bg-efficiency/15 text-efficiency">
                          <Cpu className="mr-1 size-3" /> active
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">candidate</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Error by algorithm and season" subtitle="RMSE, kWh">
          <CompareBarChart
            data={seasonProfile.map((s, i) => ({
              season: s.season,
              lstm: Math.round((models[0]!.rmse + i * 1.8) * 10) / 10,
              rf: Math.round((models[1]!.rmse + i * 2.4) * 10) / 10,
              lin: Math.round((models[3]!.rmse + i * 3.1) * 10) / 10,
            }))}
            xKey="season"
            unit=" kWh"
            height={260}
            bars={[
              { key: "lstm", name: "LSTM", tone: "chart-1" },
              { key: "rf", name: "Random Forest", tone: "chart-3" },
              { key: "lin", name: "Linear Regression", tone: "chart-2" },
            ]}
          />
        </Panel>
      </div>
    </AppShell>
  );
}
