import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { Panel } from "@/components/ui-kit";
import { energyChartPoints, localAxisLabel } from "@/lib/dashboard-view";
export function EnergyHistoryChart({
  points,
  total,
}: {
  points: { timestamp: string; Appliances: number }[];
  total: number;
}) {
  const data = energyChartPoints(points);
  return (
    <Panel
      title="Recorded Appliances energy"
      subtitle="Stored observations in Wh; building-local timestamps"
    >
      <p className="mb-3 text-sm text-muted-foreground">
        Showing {points.length} of {total} stored measurements. Points are not connected or
        interpolated; blank time ranges remain visible.
      </p>
      {data.length ? (
        <>
          <div className="h-[280px] min-w-0" data-energy-points={points.length}>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 15, right: 15, bottom: 25, left: 0 }}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                <XAxis
                  dataKey="x"
                  type="number"
                  domain={["dataMin", "dataMax"]}
                  tickFormatter={(v) => localAxisLabel(Number(v))}
                  tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                  minTickGap={45}
                  name="Timestamp (local)"
                />
                <YAxis
                  dataKey="Appliances"
                  type="number"
                  name="Appliances"
                  unit=" Wh"
                  tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    const point = payload?.[0]?.payload as (typeof data)[number] | undefined;
                    return active && point ? (
                      <div className="rounded-md border bg-popover p-3 text-xs text-popover-foreground">
                        <p>{point.timestamp.replace("T", " ")} (local)</p>
                        <p>Measured Appliances: {point.Appliances} Wh</p>
                      </div>
                    ) : null;
                  }}
                />
                <Scatter
                  name="Measured Appliances (Wh)"
                  data={data}
                  fill="var(--efficiency)"
                  isAnimationActive={false}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 break-words text-xs text-muted-foreground">
            Displayed range: {points[0]?.timestamp} to {points.at(-1)?.timestamp} (local)
          </p>
        </>
      ) : (
        <p>No measurements are stored for this building.</p>
      )}
    </Panel>
  );
}
