import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { Panel, StatCard } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { buildings, recommendations as seed, type Recommendation } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/recommendations")({
  head: () => ({
    meta: [
      { title: "Recommendations — Smart Energy AI" },
      {
        name: "description",
        content:
          "System-generated energy savings recommendations ranked by impact, with status tracking from new to applied.",
      },
      { property: "og:title", content: "Recommendations — Smart Energy AI" },
      { property: "og:description", content: "Ranked savings actions with comfort-risk scoring." },
    ],
  }),
  component: RecommendationsPage,
});

const statuses = ["all", "new", "in_progress", "applied", "dismissed"] as const;
const labels: Record<string, string> = {
  all: "All",
  new: "New",
  in_progress: "In progress",
  applied: "Applied",
  dismissed: "Dismissed",
};

function RecommendationsPage() {
  const [items, setItems] = useState<Recommendation[]>(seed);
  const [filter, setFilter] = useState<(typeof statuses)[number]>("all");

  const visible = items
    .filter((r) => filter === "all" || r.status === filter)
    .sort((a, b) => b.savingKwh - a.savingKwh);

  const setStatus = (id: string, status: Recommendation["status"]) => {
    setItems((prev) => prev.map((r) => (r.id === id ? { ...r, status } : r)));
    toast.success(`Recommendation marked as ${labels[status]!.toLowerCase()}.`);
  };

  return (
    <AppShell
      title="Recommendations"
      subtitle="Ranked by projected impact · comfort-constrained optimizer"
      actions={
        <Tabs value={filter} onValueChange={(v) => setFilter(v as typeof filter)}>
          <TabsList className="h-8">
            {statuses.map((s) => (
              <TabsTrigger key={s} value={s} className="text-xs">
                {labels[s]}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      }
    >
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard
            label="Projected weekly saving"
            value={items.filter((r) => r.status !== "dismissed").reduce((s, r) => s + r.savingKwh, 0)}
            unit="kWh"
          />
          <StatCard
            label="Applied this month"
            value={items.filter((r) => r.status === "applied").length}
            unit="actions"
            tone="info"
          />
          <StatCard
            label="High-impact open"
            value={items.filter((r) => r.impact === "high" && r.status === "new").length}
            unit="items"
            tone="peak"
          />
        </div>

        <div className="space-y-3">
          {visible.map((r) => {
            const b = buildings.find((x) => x.id === r.buildingId);
            return (
              <article key={r.id} className="panel p-5">
                <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                          r.impact === "high"
                            ? "bg-efficiency/15 text-efficiency"
                            : r.impact === "medium"
                              ? "bg-peak/15 text-peak"
                              : "bg-muted text-muted-foreground",
                        )}
                      >
                        {r.impact} impact
                      </span>
                      <span className="font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
                        {b?.name} · comfort risk: {r.comfortRisk}
                      </span>
                    </div>
                    <h3 className="mt-2.5 text-base font-semibold">{r.title}</h3>
                    <p className="mt-1.5 text-sm text-muted-foreground">{r.detail}</p>
                    <p className="mt-3 font-mono text-[11px] text-efficiency">
                      −{r.savingKwh} kWh/week · €{r.savingEur.toFixed(2)}/day · generated {r.createdAt}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-col gap-2">
                    <span
                      className={cn(
                        "rounded-lg border px-2.5 py-1 text-center text-[10px] font-semibold uppercase",
                        r.status === "applied"
                          ? "border-efficiency/40 text-efficiency"
                          : r.status === "in_progress"
                            ? "border-peak/40 text-peak"
                            : r.status === "dismissed"
                              ? "border-border text-muted-foreground"
                              : "border-info/40 text-info",
                      )}
                    >
                      {labels[r.status]}
                    </span>
                    {r.status !== "applied" ? (
                      <Button size="sm" variant="energy" onClick={() => setStatus(r.id, "applied")}>
                        Apply
                      </Button>
                    ) : null}
                    {r.status === "new" ? (
                      <Button size="sm" variant="outline" onClick={() => setStatus(r.id, "in_progress")}>
                        Start
                      </Button>
                    ) : null}
                    {r.status !== "dismissed" ? (
                      <Button size="sm" variant="ghost" onClick={() => setStatus(r.id, "dismissed")}>
                        Dismiss
                      </Button>
                    ) : null}
                  </div>
                </div>
              </article>
            );
          })}
          {visible.length === 0 ? (
            <Panel>
              <p className="py-8 text-center text-sm text-muted-foreground">
                Nothing in this state right now.
              </p>
            </Panel>
          ) : null}
        </div>
      </div>
    </AppShell>
  );
}
