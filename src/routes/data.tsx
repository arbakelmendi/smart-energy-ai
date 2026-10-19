import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Download, FileSpreadsheet, Search, Upload } from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { Panel, StatCard } from "@/components/ui-kit";
import { CompareBarChart, TrendAreaChart } from "@/components/charts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { hourlyProfile, readings, seasonProfile, weekdayProfile } from "@/lib/mock-data";

export const Route = createFileRoute("/data")({
  head: () => ({ meta: [{ title: "Operational service not connected | SmartEnergyAI" }, { name: "description", content: "No verified operational data or management service is connected to this prototype." }] }),
  component: DataPage,
});

type SortKey = "timestamp" | "kwh" | "temperature" | "occupants";

function DataPage() {
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<SortKey>("timestamp");
  const [asc, setAsc] = useState(false);

  const rows = useMemo(() => {
    const filtered = readings.filter((r) =>
      `${r.building} ${r.timestamp} ${r.dayType}`.toLowerCase().includes(q.toLowerCase()),
    );
    return [...filtered].sort((a, b) => {
      const av = a[sort];
      const bv = b[sort];
      const cmp = typeof av === "string" ? av.localeCompare(String(bv)) : Number(av) - Number(bv);
      return asc ? cmp : -cmp;
    });
  }, [q, sort, asc]);

  const header = (key: SortKey, label: string) => (
    <th className="px-4 py-3 font-medium">
      <button
        className="hover:text-efficiency"
        onClick={() => {
          if (sort === key) setAsc((v) => !v);
          else {
            setSort(key);
            setAsc(true);
          }
        }}
      >
        {label}
        {sort === key ? (asc ? " ↑" : " ↓") : ""}
      </button>
    </th>
  );

  return (
    <AppShell
      title="Data & reports"
      subtitle={`${readings.length} readings in view · 2.94M rows in warehouse`}
      actions={
        <>
          <Button size="sm" variant="wire" onClick={() => toast.success("CSV parsed: 18,240 rows staged for import.")}>
            <Upload className="size-3.5" /> Import CSV
          </Button>
          <Button size="sm" variant="ghost" onClick={() => toast.success("report-2026-02-12.pdf generated.")}>
            <Download className="size-3.5" /> Export PDF
          </Button>
          <Button size="sm" variant="ghost" onClick={() => toast.success("readings-export.csv downloaded.")}>
            <Download className="size-3.5" /> Export CSV
          </Button>
        </>
      }
    >
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Rows ingested" value={2_940_000} unit="rows" icon={<FileSpreadsheet className="size-4" />} />
          <StatCard label="Coverage" value={99.4} decimals={1} unit="%" delta="4 gaps interpolated" />
          <StatCard label="Mean load" value={812.6} decimals={1} unit="kWh/day" tone="info" />
          <StatCard label="Peak recorded" value={2288} unit="kWh" tone="peak" delta="Albi Retail · 21 Dec" />
        </div>

        <Panel title="Last upload preview" subtitle="hospital_wingC_2025Q4.csv · first rows">
          <pre className="overflow-x-auto rounded-xl border border-border bg-surface-2/60 p-4 font-mono text-[11px] text-muted-foreground">
{`timestamp,kwh,temperature,humidity,occupants
2025-10-01 00:00,48.2,11.4,73,38
2025-10-01 00:15,47.6,11.2,74,36
2025-10-01 00:30,46.9,11.1,74,35
2025-10-01 00:45,46.4,10.9,75,34`}
          </pre>
        </Panel>

        <div className="grid gap-4 lg:grid-cols-3">
          <Panel title="By time of day">
            <TrendAreaChart data={hourlyProfile} xKey="hour" dataKey="kwh" height={200} />
          </Panel>
          <Panel title="By day of week">
            <CompareBarChart data={weekdayProfile} xKey="day" height={200} bars={[{ key: "kwh", name: "Actual", tone: "chart-1" }]} highlightMax />
          </Panel>
          <Panel title="By season">
            <CompareBarChart data={seasonProfile} xKey="season" height={200} bars={[{ key: "kwh", name: "Actual", tone: "chart-3" }]} highlightMax />
          </Panel>
        </div>

        <Panel
          title="Historical readings"
          subtitle="search, sort and inspect raw records"
          bodyClassName="p-0"
          action={
            <div className="relative">
              <Search className="pointer-events-none absolute top-2.5 left-2.5 size-3.5 text-muted-foreground" />
              <Input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Filter by building or date…"
                className="h-8 w-[240px] pl-8 text-xs"
              />
            </div>
          }
        >
          <div className="max-h-[520px] overflow-auto">
            <table className="w-full min-w-[720px] text-sm">
              <thead className="sticky top-0 border-b border-border bg-surface text-left">
                <tr className="font-mono text-[10px] tracking-[0.16em] text-muted-foreground uppercase">
                  {header("timestamp", "Timestamp")}
                  <th className="px-4 py-3 font-medium">Building</th>
                  {header("kwh", "kWh")}
                  {header("temperature", "Temp °C")}
                  <th className="px-4 py-3 font-medium">RH %</th>
                  {header("occupants", "Occupants")}
                  <th className="px-4 py-3 font-medium">Day type</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={`${r.timestamp}-${r.building}`} className="border-b border-border/50 hover:bg-muted/40">
                    <td className="px-4 py-2.5 font-mono text-xs">{r.timestamp}</td>
                    <td className="px-4 py-2.5">{r.building}</td>
                    <td className="stat-number px-4 py-2.5">{r.kwh}</td>
                    <td className="stat-number px-4 py-2.5">{r.temperature}</td>
                    <td className="stat-number px-4 py-2.5 text-muted-foreground">{r.humidity}</td>
                    <td className="stat-number px-4 py-2.5">{r.occupants}</td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">{r.dayType}</td>
                  </tr>
                ))}
                {rows.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-10 text-center text-sm text-muted-foreground">
                      No readings match “{q}”.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>
    </AppShell>
  );
}
