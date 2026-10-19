import { useHealth, useModelInfo } from "@/hooks/use-smart-energy-api";
import { cn } from "@/lib/utils";

/** Only this compact element reflects real API resources; dashboard demos remain for Phase 17. */
export function BackendStatus() {
  const health = useHealth();
  const connected = !health.isError && health.data?.status === "ok";
  const model = useModelInfo(connected);
  const pending = health.isPending || health.isFetching;
  const label = pending ? "Checking API?" : connected ? "API connected" : "Backend unavailable";

  return (
    <div className="flex flex-col items-end gap-1">
      <div role="status" aria-live="polite" className="flex items-center gap-2 rounded-full border border-border bg-surface/70 px-3 py-1.5">
        <span aria-hidden="true" className={cn("size-1.5 rounded-full", pending ? "bg-muted-foreground" : connected ? "bg-efficiency" : "bg-peak")} />
        <span className={cn("font-mono text-[10px] tracking-wider uppercase", connected && !pending ? "text-efficiency" : "text-muted-foreground")}>
          {label}
        </span>
        {!pending && (!connected || model.isError) ? (
          <button type="button" className="text-[10px] underline underline-offset-2" aria-label="Retry backend connection"
            onClick={() => { void health.refetch(); if (connected) void model.refetch(); }}>
            Retry
          </button>
        ) : null}
      </div>
      {connected && !pending ? (
        <span className="hidden text-[10px] text-muted-foreground md:block">
          {model.isError ? "Model info unavailable" : model.data
            ? `${model.data.model_name} ? ${model.data.forecast_horizon_minutes} min ? ${model.data.unit} ? ${model.data.feature_count} features`
            : "Loading model info?"}
        </span>
      ) : null}
    </div>
  );
}
