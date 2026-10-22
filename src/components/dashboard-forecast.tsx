import { Panel } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import { useCreateBuildingPrediction } from "@/hooks/use-building-predictions";
import { ApiError } from "@/lib/api/client";
import type { BuildingDashboardSummary } from "@/lib/api/dashboard";
export function DashboardForecast({
  data,
  refreshing,
}: {
  data: BuildingDashboardSummary;
  refreshing: boolean;
}) {
  const mutation = useCreateBuildingPrediction(data.building.id);
  const prediction = refreshing ? null : data.current_prediction;
  const payload = mutation.error instanceof ApiError ? mutation.error.detail : null;
  const detail =
    payload && typeof payload === "object" && "detail" in payload ? payload.detail : null;
  const message =
    detail && typeof detail === "object" && "message" in detail
      ? String(detail.message)
      : mutation.error?.message;
  return (
    <Panel title="Current forecast and recommendation">
      <div
        className="space-y-3 text-sm"
        data-current-forecast={prediction ? prediction.id : "none"}
      >
        <p className="text-muted-foreground">
          The model was validated on the UCI reference building. Forecasts for other buildings are
          experimental. Recommendations are decision support only.
        </p>
        {refreshing ? (
          <p role="status">Refreshing the current stored state...</p>
        ) : prediction ? (
          <>
            <p className="text-2xl font-semibold">
              Predicted next {prediction.horizon_minutes}-minute energy:{" "}
              {prediction.prediction_wh.toFixed(3)} Wh
            </p>
            <p>Source (local): {prediction.source_timestamp.replace("T", " ")}</p>
            <p>Forecast (local): {prediction.forecast_timestamp.replace("T", " ")}</p>
            {prediction.recommendation ? (
              <div
                className="rounded-md border p-3"
                data-current-recommendation={prediction.recommendation.level}
              >
                <p>
                  Recommendation: {prediction.recommendation.level} | Priority:{" "}
                  {prediction.recommendation.priority}
                </p>
                <p className="mt-2">{prediction.recommendation.text}</p>
              </div>
            ) : (
              <p>No recommendation snapshot is available.</p>
            )}
          </>
        ) : (
          <>
            <p className="font-medium">No current forecast yet</p>
            {data.latest_stored_prediction ? (
              <p>
                A historical forecast is stored for source{" "}
                {data.latest_stored_prediction.source_timestamp.replace("T", " ")}; it does not
                match the current inputs.
              </p>
            ) : (
              <p>No forecast has been stored for this building.</p>
            )}
          </>
        )}
        {!prediction ? (
          <Button
            disabled={refreshing || !data.readiness.ready || mutation.isPending}
            onClick={async () => {
              try {
                await mutation.mutateAsync();
              } catch {
                /* Shown below. */
              }
            }}
          >
            {mutation.isPending ? "Predicting..." : "Predict next 10 minutes"}
          </Button>
        ) : null}
        {!data.readiness.ready ? <p>Forecast unavailable: {data.readiness.message}</p> : null}
        {message ? (
          <p role="alert" className="text-destructive">
            {message}
          </p>
        ) : null}
      </div>
    </Panel>
  );
}
