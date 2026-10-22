import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Panel } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import { BuildingSelection } from "@/components/building-selection";
import { useBuildingPredictions } from "@/hooks/use-building-predictions";
import type { Building } from "@/lib/api/buildings";
function Ledger({
  building,
  mode,
}: {
  building: Building;
  mode: "predictions" | "recommendations";
}) {
  const [offset, setOffset] = useState(0);
  const query = useBuildingPredictions(building.id, 50, offset);
  if (query.isError)
    return (
      <Panel title="History unavailable">
        <p role="alert">{query.error.message}</p>
        <Button
          onClick={() => {
            void query.refetch();
          }}
        >
          Retry history
        </Button>
      </Panel>
    );
  if (query.isPending) return <p role="status">Loading saved history...</p>;
  return (
    <Panel
      title={`${building.name}: ${mode === "predictions" ? "prediction history" : "saved recommendation ledger"}`}
    >
      <div className="space-y-4 text-sm">
        <p>
          Persisted forecast snapshots, newest saved first. Historical recommendations are not
          active alerts. Use the dashboard to check current inputs.
        </p>
        <Link className="underline" to="/dashboard" search={{ building: String(building.id) }}>
          Open building dashboard
        </Link>
        <p data-history-total={query.data.total}>Stored forecasts: {query.data.total}</p>
        {!query.data.items.length ? (
          <p>No saved forecasts on this page.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr>
                  <th className="p-2">Building / Forecast (local)</th>
                  <th>Predicted Wh</th>
                  <th>Saved recommendation</th>
                  <th>Created (UTC)</th>
                  <th>Context</th>
                </tr>
              </thead>
              <tbody>
                {query.data.items.map((item) => (
                  <tr key={item.id} className="border-t">
                    <td className="whitespace-nowrap p-2">
                      {building.name}
                      <br />
                      Source: {item.source_timestamp.replace("T", " ")}
                      <br />
                      Forecast: {item.forecast_timestamp.replace("T", " ")}
                    </td>
                    <td className="p-2">{item.prediction_wh.toFixed(3)}</td>
                    <td className="min-w-[180px] p-2">
                      {item.recommendation ? (
                        <>
                          <strong>{item.recommendation.level}</strong>
                          {mode === "recommendations" ? (
                            <>
                              <p>Priority: {item.recommendation.priority}</p>
                              <p>{item.recommendation.text}</p>
                            </>
                          ) : null}
                        </>
                      ) : (
                        "No snapshot stored"
                      )}
                    </td>
                    <td className="whitespace-nowrap p-2">{item.created_at.replace("T", " ")}</td>
                    <td className="p-2">
                      {!query.isFetching && item.matches_current_history
                        ? "Matches assessed inputs"
                        : "Historical / checking"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="flex flex-wrap gap-3">
          <Button
            variant="wire"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - 50))}
          >
            Previous history
          </Button>
          <span>Offset {offset}</span>
          <Button
            variant="wire"
            disabled={offset + 50 >= query.data.total}
            onClick={() => setOffset(offset + 50)}
          >
            Next history
          </Button>
        </div>
      </div>
    </Panel>
  );
}
export function BuildingHistoryExplorer({
  selected,
  onSelect,
  mode,
}: {
  selected: string | undefined;
  onSelect: (id: string) => void;
  mode: "predictions" | "recommendations";
}) {
  return (
    <BuildingSelection selected={selected} onSelect={onSelect}>
      {(building) => <Ledger building={building} mode={mode} />}
    </BuildingSelection>
  );
}
