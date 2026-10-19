/** Provenance: model/info; analysis/model-comparison; analysis/feature-importance; recommendations/thresholds. */
import type { ReactNode } from "react";
import { Activity, Clock, Cpu, Target } from "lucide-react";
import { useModelInfo, useModelComparison, useFeatureImportance, useRecommendationThresholds } from "@/hooks/use-smart-energy-api";
import { Panel, MetricPill } from "@/components/ui-kit";
import { ResearchBarChart } from "@/components/charts";
import type { RecommendationThresholdsResponse } from "@/lib/api/types";

function DataState({ pending, error, retry, children }: { pending: boolean; error: boolean; retry: () => void; children: ReactNode }) {
  if (error) return <div role="alert" className="rounded-xl border border-border bg-surface-2/50 p-5 text-sm text-muted-foreground">
    Verified data unavailable. <button type="button" onClick={retry} className="ml-2 text-efficiency underline underline-offset-2">Retry data</button>
  </div>;
  if (pending) return <p role="status" className="animate-pulse py-8 text-sm text-muted-foreground">Loading verified data...</p>;
  return <>{children}</>;
}

export function ModelPerformance() {
  const query = useModelInfo();
  const data = query.data;
  return <Panel title="Model performance" subtitle="Held-out test | selected final model only">
    <DataState pending={query.isPending} error={query.isError} retry={() => { void query.refetch(); }}>
      {data ? <>
        <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
          <div><p className="flex items-center gap-2 text-lg font-semibold"><Cpu className="size-5 shrink-0 text-efficiency" />{data.model_name}</p>
            <p className="mt-1 text-xs text-muted-foreground">Appliances energy | {data.unit} | {data.feature_count} engineered features</p></div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-xs"><Clock className="size-3.5" />{data.forecast_horizon_minutes}-minute forecast horizon</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <MetricPill label="Held-out test MAE" value={`${data.final_held_out_metrics.mae.toFixed(3)} ${data.unit}`} hint="Mean absolute error" />
          <MetricPill label="Held-out test RMSE" value={`${data.final_held_out_metrics.rmse.toFixed(3)} ${data.unit}`} hint="Root mean squared error" />
          <MetricPill label="Held-out test R-squared" value={data.final_held_out_metrics.r2.toFixed(3)} hint="Dimensionless; not a percentage accuracy" />
        </div>
        <p className="mt-4 text-xs text-muted-foreground">Research evaluation, not current building measurements. Final selection used validation results before the held-out test.</p>
      </> : null}
    </DataState>
  </Panel>;
}

export function ValidationComparison() {
  const query = useModelComparison(); const data = query.data;
  return <Panel title="Validation comparison" subtitle="Validation RMSE (Wh) | lower is better">
    <DataState pending={query.isPending} error={query.isError} retry={() => { void query.refetch(); }}>
      {data ? <>
        <ResearchBarChart data={data.models.map((row) => ({ ...row }))} labelKey="model" valueKey="rmse" label="Validation RMSE" unit={` ${data.unit}`} />
        <p className="mt-3 text-xs text-muted-foreground">Selected: {data.selected_model} | validation RMSE {data.selected_validation_rmse.toFixed(3)} {data.unit}. These are validation results for all six approaches; final held-out test performance belongs only to the selected model.</p>
        <details className="mt-4 text-xs"><summary className="cursor-pointer text-efficiency">All validation metrics</summary>
          <div className="mt-3 overflow-x-auto"><table className="w-full min-w-[440px] text-left">
            <caption className="sr-only">Validation model comparison; MAE and RMSE in Wh</caption>
            <thead><tr><th className="py-2">Model</th><th>MAE (Wh)</th><th>RMSE (Wh)</th><th>R-squared</th></tr></thead>
            <tbody>{data.models.map((row) => <tr key={row.model} className="border-t border-border"><th className="py-2 font-medium">{row.model}</th><td>{row.mae.toFixed(3)}</td><td>{row.rmse.toFixed(3)}</td><td>{row.r2.toFixed(3)}</td></tr>)}</tbody>
          </table></div>
        </details>
      </> : null}
    </DataState>
  </Panel>;
}

export function FeatureImportance() {
  const query = useFeatureImportance(); const data = query.data;
  return <Panel title="Feature importance" subtitle="Top 10 normalized XGBoost gain | research interpretation">
    <DataState pending={query.isPending} error={query.isError} retry={() => { void query.refetch(); }}>
      {data ? <>
        <ResearchBarChart data={[...data.features].sort((a, b) => a.gain_rank - b.gain_rank).slice(0, 10).map((row) => ({ ...row }))}
          labelKey="feature" valueKey="normalized_gain" label="Normalized gain" height={360} />
        <p className="mt-3 text-xs text-muted-foreground">Predictive importance, not causal effect. Values are normalized gain fractions, not energy shares or achievable reductions.</p>
        <p className="mt-2 text-xs text-muted-foreground">{data.gain_dataset}. {data.normalized_gain_definition}.</p>
      </> : null}
    </DataState>
  </Panel>;
}

function bandLabel(definition: string, data: RecommendationThresholdsResponse) {
  let label = definition.replaceAll("prediction", "Forecast");
  for (const [key, value] of Object.entries(data.percentiles_wh)) label = label.replaceAll(key, `${value} ${data.unit}`);
  return label;
}

export function RecommendationBands() {
  const query = useRecommendationThresholds(); const data = query.data;
  return <Panel title="Recommendation thresholds" subtitle="Forecast-based decision support | development-calibrated bands">
    <DataState pending={query.isPending} error={query.isError} retry={() => { void query.refetch(); }}>
      {data ? <>
        <div className="grid gap-3 sm:grid-cols-2">{Object.entries(data.level_definitions).map(([level, definition]) =>
          <div key={level} className="rounded-xl border border-border bg-surface-2/50 p-4">
            <p className="font-mono text-xs font-semibold text-efficiency">{level}</p>
            <p className="mt-2 text-sm">{bandLabel(definition, data)}</p>
          </div>)}</div>
        <p className="mt-4 text-xs text-muted-foreground">Appliances energy for the next {data.forecast_horizon_minutes} minutes. Calibrated on TRAIN + VALIDATION ({data.calibration_rows.toLocaleString("en-US")} observations); TEST was not used for these thresholds.</p>
      </> : null}
    </DataState>
  </Panel>;
}

export function LiveDataState() {
  return <Panel title="Live data connection" subtitle="Not connected">
    <div className="grid gap-5 sm:grid-cols-2">
      <div><p className="flex items-center gap-2 text-sm font-medium"><Activity className="size-4 text-peak" />Live forecast awaiting sensor history</p>
        <p className="mt-2 text-sm text-muted-foreground">Current readings and enough recent history are needed before a forecast can be shown. No live historical feed is connected.</p></div>
      <div><p className="flex items-center gap-2 text-sm font-medium"><Target className="size-4 text-info" />No active recommendation</p>
        <p className="mt-2 text-sm text-muted-foreground">Recommendations will need a valid forecast. Decision support only; no automatic equipment control or guaranteed savings.</p></div>
    </div>
  </Panel>;
}
