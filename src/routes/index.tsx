import { createFileRoute, Link } from "@tanstack/react-router";
import {
  ArrowRight,
  Brain,
  Building2,
  CircuitBoard,
  Cpu,
  GraduationCap,
  Hospital,
  Home,
  LineChart,
  Lightbulb,
  ShoppingBag,
  Signal,
  Sparkles,
  TrendingDown,
} from "lucide-react";
import { PublicLayout } from "@/components/public-layout";
import { EnergyWave, Sparkline } from "@/components/energy-wave";
import { CountUp } from "@/components/count-up";
import { ActualVsPredictedChart, TrendAreaChart } from "@/components/charts";
import { SectionHeading, MetricPill } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import { buildTrend, hourlyProfile, models } from "@/lib/mock-data";
import heroImage from "@/assets/hero-control-room.jpg";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Smart Energy AI — Predict. Optimize. Save energy with AI." },
      {
        name: "description",
        content:
          "ML-powered forecasting and optimization of energy consumption for schools, hospitals, offices, retail and residential buildings. Live dashboards, model metrics and savings recommendations.",
      },
      { property: "og:title", content: "Smart Energy AI — Predict. Optimize. Save energy with AI." },
      {
        property: "og:description",
        content:
          "Forecast building consumption from temperature, humidity, season, occupancy and time of day — and act on ranked savings recommendations.",
      },
    ],
  }),
  component: Landing,
});

const trend = buildTrend(30, 1, 3);
const activeModel = models[0]!;

const steps = [
  {
    icon: Signal,
    title: "Data collection",
    text: "Sensors, meters and CSV imports stream consumption, temperature, humidity and occupancy at 15-minute resolution.",
  },
  {
    icon: Brain,
    title: "Predictive model",
    text: "Feature engineering on season, hour, day-of-week and occupancy feeds an LSTM ensemble benchmarked against Random Forest and regression baselines.",
  },
  {
    icon: Lightbulb,
    title: "Recommendations",
    text: "The optimizer searches setpoint and scheduling changes that cut kWh while keeping predicted comfort deviation inside limits.",
  },
  {
    icon: TrendingDown,
    title: "Verified savings",
    text: "Applied actions are measured against the counterfactual forecast, so every kWh saved is attributable and auditable.",
  },
];

const useCases = [
  {
    icon: GraduationCap,
    title: "Schools & universities",
    kpi: "13.4% average reduction",
    text: "Timetable-aware setbacks for classrooms and labs that sit empty between blocks.",
  },
  {
    icon: Hospital,
    title: "Hospitals",
    kpi: "24/7 anomaly watch",
    text: "Peak-shaving on AHU start-up without touching critical-care air-change requirements.",
  },
  {
    icon: Building2,
    title: "Offices",
    kpi: "16.5% average reduction",
    text: "Occupancy-driven HVAC and lighting profiles across multi-tenant floors.",
  },
  {
    icon: ShoppingBag,
    title: "Shopping centers",
    kpi: "€53/day off-peak shift",
    text: "Pre-cooling moved into off-peak tariff windows using ambient-temperature forecasts.",
  },
  {
    icon: Home,
    title: "Residential",
    kpi: "11.3% average reduction",
    text: "Shared-service baseload tracking for corridors, pumps, lifts and common areas.",
  },
];

function Landing() {
  return (
    <PublicLayout>
      {/* HERO — asymmetric split, full-bleed glow */}
      <section className="mesh-bg relative overflow-hidden border-b border-border">
        <div className="grid-lines absolute inset-0 -z-10" />
        <EnergyWave className="absolute inset-x-0 bottom-0 -z-10 h-64 opacity-70" />
        <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:py-24">
          <div className="min-w-0">
            <span className="inline-flex items-center gap-2 rounded-full border border-efficiency/35 bg-efficiency/10 px-3 py-1.5 font-mono text-[11px] tracking-[0.16em] text-efficiency uppercase">
              <span className="size-1.5 rounded-full bg-efficiency pulse-dot" />
              ml forecasting engine · v4.2
            </span>
            <h1 className="mt-6 text-4xl leading-[1.05] font-bold sm:text-5xl lg:text-6xl">
              Predict. Optimize.
              <br />
              <span className="text-efficiency">Save energy with AI.</span>
            </h1>
            <p className="mt-5 max-w-xl text-base text-muted-foreground sm:text-lg">
              Smart Energy AI forecasts building consumption from temperature, humidity, season, time
              of day, day of week and occupancy — then recommends the exact changes that cut kWh
              without sacrificing comfort.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button asChild size="lg" variant="energy">
                <Link to="/signup">
                  Request a demo <ArrowRight className="size-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="wire">
                <Link to="/dashboard">Explore live dashboard</Link>
              </Button>
            </div>
            <dl className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
              {[
                { k: "kWh analysed", v: 2.94, s: "M", d: 2 },
                { k: "Buildings", v: 63, s: "", d: 0 },
                { k: "Sensors live", v: 1284, s: "", d: 0 },
                { k: "Model R²", v: 0.962, s: "", d: 3 },
              ].map((m) => (
                <div key={m.k}>
                  <dd className="stat-number text-2xl font-semibold text-foreground">
                    <CountUp value={m.v} decimals={m.d} suffix={m.s} />
                  </dd>
                  <dt className="mt-0.5 text-[11px] tracking-wide text-muted-foreground uppercase">
                    {m.k}
                  </dt>
                </div>
              ))}
            </dl>
          </div>

          <div className="relative min-w-0">
            <img
              src={heroImage}
              alt="Dark control-room visualization of live building energy telemetry"
              className="w-full rounded-3xl border border-border object-cover opacity-90 shadow-[var(--shadow-panel)]"
              width={1280}
              height={960}
              loading="eager"
            />
            <div className="panel glow-ring absolute -bottom-6 -left-2 w-[78%] p-4 sm:-left-8">
              <div className="flex items-center justify-between gap-3">
                <p className="font-mono text-[10px] tracking-[0.18em] text-muted-foreground uppercase">
                  live load · block a
                </p>
                <span className="text-xs font-semibold text-efficiency">−13.4%</span>
              </div>
              <Sparkline
                points={hourlyProfile.map((h) => h.kwh)}
                tone="efficiency"
                className="mt-3 h-14 w-full"
              />
            </div>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS — stepped timeline, not cards-in-a-row */}
      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
        <SectionHeading
          eyebrow="how it works"
          title="From raw meter readings to verified savings"
          description="Four stages, fully traceable — every recommendation can be traced back to the features and model version that produced it."
        />
        <ol className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-border bg-border md:grid-cols-2 lg:grid-cols-4">
          {steps.map((s, i) => (
            <li key={s.title} className="group bg-surface p-6 transition-colors hover:bg-surface-2">
              <div className="flex items-center justify-between">
                <span className="grid size-10 place-items-center rounded-xl border border-efficiency/35 bg-efficiency/10 text-efficiency transition-transform duration-300 group-hover:scale-110">
                  <s.icon className="size-5" strokeWidth={1.9} />
                </span>
                <span className="stat-number text-3xl font-bold text-muted-foreground/25">
                  0{i + 1}
                </span>
              </div>
              <h3 className="mt-5 text-base font-semibold">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.text}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* FULL-WIDTH CHART BAND */}
      <section className="border-y border-border bg-surface/40">
        <div className="mx-auto grid max-w-7xl gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[1fr_320px]">
          <div className="min-w-0">
            <SectionHeading
              eyebrow="model transparency"
              title="Actual vs predicted, with a 95% confidence band"
              description="30 days of aggregated portfolio consumption. Nothing is hidden behind a black box — error metrics are published on every screen."
            />
            <div className="mt-8">
              <ActualVsPredictedChart data={trend} height={330} />
            </div>
          </div>
          <div className="space-y-4">
            <MetricPill label="MAE" value={`${activeModel.mae} kWh`} hint="mean absolute error" />
            <MetricPill label="RMSE" value={`${activeModel.rmse} kWh`} hint="root mean sq. error" />
            <MetricPill label="R²" value={activeModel.r2.toFixed(3)} hint="explained variance" />
            <div className="panel p-4">
              <p className="text-xs text-muted-foreground">
                Reported reduction across the pilot portfolio
              </p>
              <p className="stat-number mt-1 text-4xl font-bold text-efficiency">
                <CountUp value={18.6} decimals={1} suffix="%" />
              </p>
              <p className="mt-1 text-[11px] text-muted-foreground">
                measured against counterfactual forecast, 2025 heating season
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* USE CASES — asymmetric grid */}
      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
        <SectionHeading
          eyebrow="use cases"
          title="Tuned for buildings that never behave the same way twice"
        />
        <div className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {useCases.map((u, i) => (
            <article
              key={u.title}
              className={`panel lift p-6 ${i === 0 ? "lg:col-span-2" : ""}`}
            >
              <div className="flex items-start justify-between gap-4">
                <span className="grid size-10 place-items-center rounded-xl bg-surface-2 text-efficiency">
                  <u.icon className="size-5" strokeWidth={1.9} />
                </span>
                <span className="rounded-full border border-border px-2.5 py-1 font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
                  {u.kpi}
                </span>
              </div>
              <h3 className="mt-5 text-lg font-semibold">{u.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{u.text}</p>
            </article>
          ))}
        </div>
      </section>

      {/* DENSE TECHNICAL BAND */}
      <section className="border-y border-border bg-surface/40">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
          <SectionHeading
            eyebrow="benchmark"
            title="Four algorithms, one leaderboard"
            description="Every model is retrained nightly on the same feature set and validated on a held-out 20% split."
          />
          <div className="panel mt-8 overflow-x-auto">
            <table className="w-full min-w-[620px] text-sm">
              <thead className="border-b border-border text-left">
                <tr className="font-mono text-[10px] tracking-[0.16em] text-muted-foreground uppercase">
                  <th className="px-5 py-3 font-medium">Algorithm</th>
                  <th className="px-5 py-3 font-medium">Family</th>
                  <th className="px-5 py-3 font-medium">MAE</th>
                  <th className="px-5 py-3 font-medium">RMSE</th>
                  <th className="px-5 py-3 font-medium">R²</th>
                  <th className="px-5 py-3 font-medium">Train time</th>
                </tr>
              </thead>
              <tbody>
                {models.map((m) => (
                  <tr key={m.name} className="border-b border-border/60 last:border-0">
                    <td className="px-5 py-3.5 font-medium">
                      <span className="flex items-center gap-2">
                        {m.active ? <Cpu className="size-4 text-efficiency" /> : <CircuitBoard className="size-4 text-muted-foreground" />}
                        {m.name}
                        {m.active ? (
                          <span className="rounded bg-efficiency/15 px-1.5 py-0.5 text-[10px] font-semibold text-efficiency">
                            ACTIVE
                          </span>
                        ) : null}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-muted-foreground">{m.type}</td>
                    <td className="stat-number px-5 py-3.5">{m.mae}</td>
                    <td className="stat-number px-5 py-3.5">{m.rmse}</td>
                    <td className="stat-number px-5 py-3.5 text-efficiency">{m.r2.toFixed(3)}</td>
                    <td className="px-5 py-3.5 text-muted-foreground">{m.trainSec}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className="panel p-5">
              <p className="text-sm font-semibold">Daily load profile (portfolio average)</p>
              <div className="mt-3">
                <TrendAreaChart data={hourlyProfile} xKey="hour" dataKey="kwh" height={200} />
              </div>
            </div>
            <div className="panel p-5">
              <p className="text-sm font-semibold">Forecast error over 30 days</p>
              <div className="mt-3">
                <TrendAreaChart
                  data={trend.map((t) => ({
                    date: t.date,
                    error: Math.round(Math.abs(t.actual - t.predicted) * 10) / 10,
                  }))}
                  dataKey="error"
                  tone="chart-2"
                  height={200}
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mesh-bg relative overflow-hidden">
        <div className="mx-auto max-w-4xl px-4 py-24 text-center sm:px-6">
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface/70 px-3 py-1.5 font-mono text-[11px] tracking-[0.16em] text-muted-foreground uppercase">
            <Sparkles className="size-3.5 text-efficiency" /> academic pilot open
          </span>
          <h2 className="mt-6 text-3xl font-bold sm:text-4xl">
            Start forecasting your building this week
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
            Upload a single CSV of historical readings and the platform will train, validate and
            publish a forecast with full error reporting in under ten minutes.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button asChild size="lg" variant="energy">
              <Link to="/signup">
                Create account <ArrowRight className="size-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link to="/contact">
                <LineChart className="size-4" /> Talk to the research team
              </Link>
            </Button>
          </div>
        </div>
      </section>
    </PublicLayout>
  );
}
