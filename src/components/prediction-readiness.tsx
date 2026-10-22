import { Panel } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import { usePredictionReadiness } from "@/hooks/use-prediction-readiness";
import type { PredictionReadiness } from "@/lib/api/prediction-readiness";
const headings: Record<PredictionReadiness["reason_code"], string> = {
  NO_MEASUREMENTS: "No measurements",
  INSUFFICIENT_HISTORY: "Not enough history",
  LATEST_WINDOW_HAS_GAPS: "History contains gaps or incompatible intervals",
  INVALID_RAW_DATA: "Stored history is invalid",
  READY: "History ready for a ten-minute forecast input",
};
export function PredictionReadinessPanel({ buildingId }: { buildingId: number }) {
  const query = usePredictionReadiness(buildingId);
  return (
    <Panel title="Prediction readiness">
      <div className="space-y-3 text-sm">
        {query.isError ? (
          <div className="space-y-2">
            <p role="alert">{query.error.message}</p>
            <Button
              onClick={() => {
                void query.refetch();
              }}
            >
              Retry readiness
            </Button>
          </div>
        ) : query.isPending ? (
          <p role="status">Checking latest history...</p>
        ) : (
          <div className="space-y-3" data-readiness-state={query.data.reason_code}>
            <h4 className="font-semibold">{headings[query.data.reason_code]}</h4>
            <p>{query.data.message}</p>
            <dl className="grid gap-3 sm:grid-cols-2">
              <div>
                <dt className="text-muted-foreground">Stored measurements</dt>
                <dd>{query.data.measurement_count}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Latest observation (local)</dt>
                <dd className="break-words">
                  {query.data.latest_measurement_timestamp?.replace("T", " ") ?? "None"}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Required history</dt>
                <dd>
                  {query.data.required_observations} observations (
                  {query.data.required_history_intervals} intervals)
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Required spacing</dt>
                <dd>{query.data.required_interval_minutes} minutes</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-muted-foreground">
                  Continuous latest history, up to the required window
                </dt>
                <dd>
                  {query.data.latest_measurement_timestamp
                    ? query.data.continuous_intervals_available + 1
                    : 0}{" "}
                  observations ({query.data.continuous_intervals_available} intervals)
                </dd>
              </div>
            </dl>
            {query.data.first_gap ? (
              <p className="break-words">
                An incompatible interval was found between{" "}
                {query.data.first_gap.before_timestamp.replace("T", " ")} and{" "}
                {query.data.first_gap.after_timestamp.replace("T", " ")} (local time).
              </p>
            ) : null}
          </div>
        )}
        <p className="text-muted-foreground">
          This checks feature compatibility only. Forecasts run only when explicitly requested. Feature
          compatibility alone does not establish model validity for a building. No missing observations are filled or
          interpolated.
        </p>
      </div>
    </Panel>
  );
}
