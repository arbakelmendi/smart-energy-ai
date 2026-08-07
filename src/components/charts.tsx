import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TrendPoint } from "@/lib/mock-data";

const axis = {
  stroke: "var(--muted-foreground)",
  fontSize: 11,
  tickLine: false,
  axisLine: false,
} as const;

function tooltipStyle() {
  return {
    contentStyle: {
      background: "var(--popover)",
      border: "1px solid var(--border)",
      borderRadius: "12px",
      fontSize: 12,
      color: "var(--popover-foreground)",
      boxShadow: "var(--shadow-panel)",
    },
    labelStyle: { color: "var(--muted-foreground)", marginBottom: 4 },
    itemStyle: { color: "var(--popover-foreground)" },
  };
}

/** Actual vs predicted consumption with a shaded confidence interval. */
export function ActualVsPredictedChart({
  data,
  height = 320,
  showBand = true,
}: {
  data: TrendPoint[];
  height?: number;
  showBand?: boolean;
}) {
  const shaped = data.map((d) => ({
    ...d,
    band: [d.lower, d.upper] as [number, number],
    actualPoint: d.actual > 0 ? d.actual : null,
  }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={shaped} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
        <defs>
          <linearGradient id="fill-actual" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--chart-1)" stopOpacity="0.42" />
            <stop offset="100%" stopColor="var(--chart-1)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="var(--grid-line)" strokeDasharray="3 6" vertical={false} />
        <XAxis dataKey="date" {...axis} interval="preserveStartEnd" minTickGap={24} />
        <YAxis {...axis} width={56} unit=" kWh" />
        <Tooltip {...tooltipStyle()} />
        <Legend
          wrapperStyle={{ fontSize: 11, color: "var(--muted-foreground)", paddingTop: 8 }}
          iconType="plainline"
        />
        {showBand && (
          <Area
            type="monotone"
            dataKey="band"
            name="95% confidence"
            stroke="none"
            fill="var(--chart-3)"
            fillOpacity={0.16}
            activeDot={false}
          />
        )}
        <Area
          type="monotone"
          dataKey="actualPoint"
          name="Actual"
          stroke="var(--chart-1)"
          strokeWidth={2.2}
          fill="url(#fill-actual)"
          dot={false}
          connectNulls
        />
        <Line
          type="monotone"
          dataKey="predicted"
          name="Predicted"
          stroke="var(--chart-2)"
          strokeWidth={2}
          strokeDasharray="5 4"
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/** Single-series gradient area chart. */
export function TrendAreaChart({
  data,
  dataKey = "actual",
  tone = "chart-1",
  height = 260,
  unit = " kWh",
}: {
  data: Array<Record<string, unknown>>;
  dataKey?: string;
  tone?: string;
  height?: number;
  unit?: string;
}) {
  const id = `fill-${tone}-${dataKey}`;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={`var(--${tone})`} stopOpacity="0.5" />
            <stop offset="100%" stopColor={`var(--${tone})`} stopOpacity="0" />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="var(--grid-line)" strokeDasharray="3 6" vertical={false} />
        <XAxis dataKey={Object.keys(data[0] ?? { date: "" })[0]} {...axis} minTickGap={20} />
        <YAxis {...axis} width={56} unit={unit} />
        <Tooltip {...tooltipStyle()} />
        <Area
          type="monotone"
          dataKey={dataKey}
          stroke={`var(--${tone})`}
          strokeWidth={2.2}
          fill={`url(#${id})`}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/** Comparison bars, optionally with a highlighted peak. */
export function CompareBarChart({
  data,
  xKey,
  bars,
  height = 260,
  unit = " kWh",
  highlightMax,
}: {
  data: Array<Record<string, unknown>>;
  xKey: string;
  bars: Array<{ key: string; name: string; tone: string }>;
  height?: number;
  unit?: string;
  highlightMax?: boolean;
}) {
  const primary = bars[0]!;
  const values = data.map((d) => Number(d[primary.key] ?? 0));
  const max = Math.max(...values);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }} barGap={4}>
        <CartesianGrid stroke="var(--grid-line)" strokeDasharray="3 6" vertical={false} />
        <XAxis dataKey={xKey} {...axis} />
        <YAxis {...axis} width={56} unit={unit} />
        <Tooltip {...tooltipStyle()} cursor={{ fill: "var(--muted)", opacity: 0.35 }} />
        {bars.length > 1 && (
          <Legend
            wrapperStyle={{ fontSize: 11, color: "var(--muted-foreground)", paddingTop: 8 }}
            iconType="circle"
          />
        )}
        {bars.map((b) => (
          <Bar key={b.key} dataKey={b.key} name={b.name} radius={[6, 6, 0, 0]} fill={`var(--${b.tone})`}>
            {highlightMax && b.key === primary.key
              ? data.map((_, i) => (
                  <Cell
                    key={i}
                    fill={values[i] === max ? "var(--chart-2)" : `var(--${b.tone})`}
                    fillOpacity={values[i] === max ? 1 : 0.8}
                  />
                ))
              : null}
          </Bar>
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Horizontal weighted bars, used for feature importance. */
export function WeightBars({ items }: { items: Array<{ feature: string; weight: number }> }) {
  const max = Math.max(...items.map((i) => i.weight));
  return (
    <ul className="space-y-3">
      {items.map((i) => (
        <li key={i.feature} className="space-y-1.5">
          <div className="flex items-center justify-between gap-3 text-xs">
            <span className="truncate text-muted-foreground">{i.feature}</span>
            <span className="stat-number shrink-0 text-foreground">{i.weight}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-efficiency transition-[width] duration-700"
              style={{ width: `${(i.weight / max) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
