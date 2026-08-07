import { createFileRoute } from "@tanstack/react-router";
import { BookOpen, FlaskConical, GraduationCap, Layers, Target } from "lucide-react";
import { PublicLayout } from "@/components/public-layout";
import { SectionHeading, MetricPill, Panel } from "@/components/ui-kit";
import { WeightBars } from "@/components/charts";
import { featureImportance, models } from "@/lib/mock-data";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: "About the project — Smart Energy AI (UBT thesis)" },
      {
        name: "description",
        content:
          "Academic context, methodology and dataset behind Smart Energy AI: an ML platform for forecasting and optimizing energy use in smart buildings.",
      },
      { property: "og:title", content: "About the project — Smart Energy AI" },
      {
        property: "og:description",
        content:
          "Research methodology: feature engineering, LSTM vs ensemble baselines, and evaluation with MAE, RMSE and R².",
      },
    ],
  }),
  component: AboutPage,
});

function AboutPage() {
  return (
    <PublicLayout>
      <section className="mesh-bg border-b border-border">
        <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:py-20">
          <p className="font-mono text-[11px] tracking-[0.2em] text-efficiency uppercase">
            academic context
          </p>
          <h1 className="mt-4 text-4xl font-bold sm:text-5xl">
            A thesis that had to run in production
          </h1>
          <p className="mt-5 text-base text-muted-foreground sm:text-lg">
            Smart Energy AI was developed at UBT — University for Business and Technology, Prishtina,
            as a bachelor thesis in Computer Science &amp; Engineering. The research question: can a
            sequence model forecast building-level electricity consumption accurately enough that its
            output can be trusted to drive automated setpoint decisions?
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { icon: GraduationCap, k: "Institution", v: "UBT — Prishtina" },
            { icon: BookOpen, k: "Field", v: "Computer Science & Engineering" },
            { icon: FlaskConical, k: "Dataset", v: "2.94M readings · 63 buildings" },
            { icon: Target, k: "Best result", v: "MAE 12.4 kWh · R² 0.962" },
          ].map((i) => (
            <div key={i.k} className="panel lift p-5">
              <i.icon className="size-5 text-efficiency" strokeWidth={1.9} />
              <p className="mt-4 font-mono text-[10px] tracking-[0.16em] text-muted-foreground uppercase">
                {i.k}
              </p>
              <p className="mt-1 text-sm font-semibold">{i.v}</p>
            </div>
          ))}
        </div>

        <div className="mt-14 grid gap-8 lg:grid-cols-[1.3fr_1fr]">
          <div className="space-y-6">
            <SectionHeading eyebrow="methodology" title="How the model is built and validated" />
            <div className="space-y-5 text-sm leading-relaxed text-muted-foreground">
              <p>
                <span className="font-medium text-foreground">Data.</span> Fifteen-minute interval
                meter readings from five pilot buildings (school, hospital wing, office tower, retail
                center, residential block), joined with local weather observations and occupancy
                counts from access-control systems. Gaps shorter than two hours are linearly
                interpolated; longer gaps are excluded from training.
              </p>
              <p>
                <span className="font-medium text-foreground">Features.</span> Outdoor temperature,
                relative humidity, hour of day (cyclically encoded), day of week, month/season,
                occupancy count, plus lagged consumption at t−1, t−24 and t−168 hours.
              </p>
              <p>
                <span className="font-medium text-foreground">Models.</span> A linear-regression
                baseline, Random Forest and XGBoost ensembles, and an LSTM with a 48-step lookback.
                All four are retrained nightly on identical splits (70/10/20 train/val/test,
                chronological) so the leaderboard remains comparable.
              </p>
              <p>
                <span className="font-medium text-foreground">Evaluation.</span> Mean absolute error,
                root mean squared error and coefficient of determination on the held-out test period,
                reported per building and aggregated. Savings claims are computed against the
                counterfactual forecast rather than a naive year-on-year comparison.
              </p>
              <p>
                <span className="font-medium text-foreground">Optimization.</span> A constrained
                search over HVAC setpoints, ventilation deadbands and scheduling windows, penalised by
                predicted comfort deviation (PMV) so no recommendation trades comfort for kWh.
              </p>
            </div>
          </div>
          <div className="space-y-4">
            <Panel title="Feature importance" subtitle="permutation importance, active LSTM">
              <WeightBars items={featureImportance} />
            </Panel>
            <div className="grid grid-cols-3 gap-3">
              <MetricPill label="MAE" value={`${models[0]!.mae}`} hint="kWh" />
              <MetricPill label="RMSE" value={`${models[0]!.rmse}`} hint="kWh" />
              <MetricPill label="R²" value={models[0]!.r2.toFixed(3)} hint="test set" />
            </div>
            <Panel title="Stack" subtitle="reproducible research environment">
              <ul className="space-y-2 text-sm text-muted-foreground">
                {[
                  "Python 3.12 · pandas · scikit-learn · TensorFlow/Keras",
                  "PostgreSQL + TimescaleDB for time-series storage",
                  "React + TypeScript front end, Recharts visualisation",
                  "Nightly retraining job with model registry and versioning",
                ].map((s) => (
                  <li key={s} className="flex items-start gap-2">
                    <Layers className="mt-0.5 size-4 shrink-0 text-efficiency" />
                    {s}
                  </li>
                ))}
              </ul>
            </Panel>
          </div>
        </div>

        <div className="panel mt-14 p-6 sm:p-8">
          <h2 className="text-xl font-semibold">Limitations and honesty notes</h2>
          <ul className="mt-4 grid gap-3 text-sm text-muted-foreground sm:grid-cols-2">
            {[
              "All figures on this deployment are simulated from the pilot distribution — the demo does not read live meters.",
              "Forecast accuracy degrades beyond a 30-day horizon because weather forecasts do, not because the model does.",
              "Occupancy data is only as good as the access-control system; buildings without turnstiles rely on a CO₂ proxy.",
              "Savings attribution assumes the counterfactual forecast stays valid, which holds only while the building envelope is unchanged.",
            ].map((t) => (
              <li key={t} className="rounded-xl border border-border bg-surface-2/50 p-4">
                {t}
              </li>
            ))}
          </ul>
        </div>
      </section>
    </PublicLayout>
  );
}
