import { useState } from "react";
import { Panel } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import { usePredictionReadiness } from "@/hooks/use-prediction-readiness";
import {
  useBuildingPredictions,
  useCreateBuildingPrediction,
} from "@/hooks/use-building-predictions";
import { ApiError } from "@/lib/api/client";
import type { BuildingPrediction } from "@/lib/api/building-predictions";
function PredictionError({ error }: { error: Error | null }) {
  if (!error) return null;
  const payload = error instanceof ApiError ? error.detail : null;
  const detail =
    payload && typeof payload === "object" && "detail" in payload ? payload.detail : null;
  const message =
    detail &&
    typeof detail === "object" &&
    "message" in detail &&
    typeof detail.message === "string"
      ? detail.message
      : error.message;
  return (
    <p role="alert" className="break-words text-sm text-destructive">
      {message}
    </p>
  );
}
function ForecastSnapshot({
  value,
  fresh,
  latest,
}: {
  value: BuildingPrediction;
  fresh: boolean;
  latest: boolean;
}) {
  return (
    <div className="space-y-3 rounded-md border p-4" data-prediction-id={value.id}>
      <h4 className="font-semibold">
        {latest ? "Latest stored forecast" : "Stored forecast snapshot"}
      </h4>
      <p className="text-2xl font-semibold">
        Predicted energy: {value.prediction_wh.toFixed(3)} Wh
      </p>
      <p className="text-sm">
        {fresh && value.matches_current_history
          ? "Matches currently assessed stored history."
          : "Historical snapshot; it is not confirmed for the current latest history."}
      </p>
      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-muted-foreground">Measured Appliances at forecast source</dt>
          <dd>
            {value.current_appliances_wh === null
              ? "Unavailable for legacy record"
              : `${value.current_appliances_wh} Wh`}
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Forecast horizon</dt>
          <dd>Next {value.horizon_minutes} minutes</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Source timestamp (local)</dt>
          <dd>{value.source_timestamp.replace("T", " ")}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Forecast timestamp (local)</dt>
          <dd>{value.forecast_timestamp.replace("T", " ")}</dd>
        </div>
      </dl>
      {value.recommendation ? (
        <div className="space-y-2 text-sm">
          <p>
            Recommendation level: <strong>{value.recommendation.level}</strong>
          </p>
          <p>{value.recommendation.text}</p>
        </div>
      ) : (
        <p className="text-sm">No recommendation snapshot exists for this legacy record.</p>
      )}
      <details className="text-sm">
        <summary className="cursor-pointer">Stored model information</summary>
        <p>{value.model_name}</p>
        <p className="break-all">SHA-256: {value.model_checksum}</p>
        <p>Created (UTC): {value.created_at.replace("T", " ")}</p>
      </details>
    </div>
  );
}
export function BuildingPredictions({ buildingId }: { buildingId: number }) {
  const [offset, setOffset] = useState(0);
  const ready = usePredictionReadiness(buildingId);
  const history = useBuildingPredictions(buildingId, 50, offset);
  const create = useCreateBuildingPrediction(buildingId);
  const disabled =
    create.isPending || ready.isPending || ready.isError || ready.isFetching || !ready.data?.ready;
  return (
    <Panel title="Building forecasts">
      <div className="space-y-4 text-sm">
        <p>
          The forecasting model was validated on the UCI reference building. Predictions for other
          buildings are experimental.
        </p>
        <p className="text-muted-foreground">
          Predictions estimate Appliances energy for the next ten-minute interval. Recommendations
          are decision support only; no automatic equipment control is performed.
        </p>
        <Button
          disabled={disabled}
          onClick={async () => {
            try {
              await create.mutateAsync();
              setOffset(0);
            } catch {
              /* Mutation error shown below. */
            }
          }}
        >
          {create.isPending ? "Predicting..." : "Predict next 10 minutes"}
        </Button>
        {!ready.data?.ready || ready.isError ? (
          <p>Compatible stored history is required. See Prediction readiness above.</p>
        ) : null}
        <PredictionError error={create.error} />
        {create.data ? (
          <p role="status">
            {create.data.reused_existing_prediction
              ? "Reused the existing stored forecast for identical inputs."
              : "Forecast and recommendation saved."}
          </p>
        ) : null}
        {history.isError ? (
          <div className="space-y-2">
            <PredictionError error={history.error} />
            <Button
              onClick={() => {
                void history.refetch();
              }}
            >
              Retry prediction history
            </Button>
          </div>
        ) : history.isPending ? (
          <p role="status">Loading prediction history...</p>
        ) : (
          <>
            <p data-prediction-count={history.data.total}>Stored forecasts: {history.data.total}</p>
            {history.data.items.length ? (
              <>
                <ForecastSnapshot
                  value={history.data.items[0]!}
                  latest={offset === 0}
                  fresh={!history.isFetching && !ready.isFetching && !!ready.data?.ready}
                />
                <div className="max-w-full overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr>
                        {[
                          "Created (UTC)",
                          "Source (local)",
                          "Forecast (local)",
                          "Predicted Wh",
                          "Recommendation",
                        ].map((h) => (
                          <th className="whitespace-nowrap p-2" key={h}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {history.data.items.map((item) => (
                        <tr key={item.id} className="border-t" data-prediction-history-id={item.id}>
                          <td className="whitespace-nowrap p-2">
                            {item.created_at.replace("T", " ")}
                          </td>
                          <td className="whitespace-nowrap p-2">
                            {item.source_timestamp.replace("T", " ")}
                          </td>
                          <td className="whitespace-nowrap p-2">
                            {item.forecast_timestamp.replace("T", " ")}
                          </td>
                          <td className="p-2">{item.prediction_wh.toFixed(3)}</td>
                          <td className="p-2">{item.recommendation?.level ?? "Not stored"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <p>
                No stored forecasts on this page. Forecasts run only after your explicit request.
              </p>
            )}
            <div className="flex flex-wrap items-center gap-3">
              <Button
                variant="wire"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - 50))}
              >
                Previous forecasts
              </Button>
              <span>Forecast offset {offset}; up to 50 rows</span>
              <Button
                variant="wire"
                disabled={offset + 50 >= history.data.total}
                onClick={() => setOffset(offset + 50)}
              >
                Next forecasts
              </Button>
            </div>
          </>
        )}
      </div>
    </Panel>
  );
}
