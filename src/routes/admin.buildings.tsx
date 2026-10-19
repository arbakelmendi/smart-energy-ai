import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { Panel } from "@/components/ui-kit";
import { buildings } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/admin/buildings")({
  head: () => ({ meta: [{ title: "Operational service not connected | SmartEnergyAI" }, { name: "description", content: "No verified operational data or management service is connected to this prototype." }] }),
  component: AdminBuildings,
});

function AdminBuildings() {
  return (
    <AppShell title="All buildings" subtitle="Cross-tenant inventory">
      <Panel bodyClassName="p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead className="border-b border-border text-left font-mono text-[10px] tracking-[0.16em] text-muted-foreground uppercase">
              <tr>
                <th className="px-5 py-3 font-medium">Building</th>
                <th className="px-5 py-3 font-medium">Type</th>
                <th className="px-5 py-3 font-medium">Area m²</th>
                <th className="px-5 py-3 font-medium">Load kWh/day</th>
                <th className="px-5 py-3 font-medium">Saving</th>
                <th className="px-5 py-3 font-medium">Sensors</th>
                <th className="px-5 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {buildings.map((b) => (
                <tr key={b.id} className="border-b border-border/50 hover:bg-muted/40">
                  <td className="px-5 py-3">
                    <Link to="/buildings/$id" params={{ id: b.id }} className="font-medium hover:text-efficiency">
                      {b.name}
                    </Link>
                    <p className="text-xs text-muted-foreground">{b.address}</p>
                  </td>
                  <td className="px-5 py-3 text-xs">{b.type}</td>
                  <td className="stat-number px-5 py-3">{b.areaM2.toLocaleString("en-US")}</td>
                  <td className="stat-number px-5 py-3">{b.currentKwh}</td>
                  <td className="stat-number px-5 py-3 text-efficiency">−{b.savingsPct}%</td>
                  <td className="stat-number px-5 py-3">{b.sensors}</td>
                  <td className="px-5 py-3">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                        b.status === "peak"
                          ? "bg-peak/15 text-peak"
                          : b.status === "watch"
                            ? "bg-muted text-muted-foreground"
                            : "bg-efficiency/15 text-efficiency",
                      )}
                    >
                      {b.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </AppShell>
  );
}
