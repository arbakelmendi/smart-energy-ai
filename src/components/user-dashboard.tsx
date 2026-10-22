import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Panel } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import { BuildingSelection } from "@/components/building-selection";
import { EnergyHistoryChart } from "@/components/energy-history-chart";
import { DashboardForecast } from "@/components/dashboard-forecast";
import { useBuildingDashboard } from "@/hooks/use-building-dashboard";
import type { Building } from "@/lib/api/buildings";
const readinessNames = {
  NO_MEASUREMENTS: "No measurements",
  INSUFFICIENT_HISTORY: "More history required",
  LATEST_WINDOW_HAS_GAPS: "History gap detected",
  INVALID_RAW_DATA: "Stored data invalid",
  READY: "Ready",
};
function SummaryCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="panel min-w-0 break-words p-5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-2 text-xl font-semibold" data-summary-label={label}>
        {value}
      </p>
    </div>
  );
}
function SelectedDashboard({ building }: { building: Building }) {
  const [limit, setLimit] = useState(144);
  const query = useBuildingDashboard(building.id, limit);
  if (query.isError)
    return (
      <Panel title="Dashboard unavailable">
        <p role="alert">{query.error.message}</p>
        <Button
          onClick={() => {
            void query.refetch();
          }}
        >
          Retry dashboard
        </Button>
      </Panel>
    );
  if (query.isPending) return <p role="status">Loading stored building state...</p>;
  const data = query.data;
  const selected = data.building;
  return (
    <div className="space-y-5" data-dashboard-building={selected.id}>
      <Panel title={selected.name}>
        <div className="flex flex-wrap gap-3 text-sm">
          <span>{selected.building_type ?? "Type not specified"}</span>
          {selected.city ? <span>{selected.city}</span> : null}
          {selected.floor_area_m2 !== null ? <span>{selected.floor_area_m2} m2</span> : null}
          <Link className="underline" to="/buildings/$id" params={{ id: String(selected.id) }}>
            Manage measurements and building
          </Link>
        </div>
        <Button
          variant="wire"
          className="mt-3"
          disabled={query.isFetching}
          onClick={() => {
            void query.refetch();
          }}
        >
          Refresh stored state
        </Button>
        <p className="mt-2 text-xs text-muted-foreground">
          Metadata provides application context; it is not part of the model input. Measurements are
          manually entered or CSV imported, not a live feed.
        </p>
      </Panel>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard label="Stored measurements" value={data.measurement_count} />
        <SummaryCard
          label="Latest stored Appliances"
          value={
            data.latest_measurement === null
              ? "No measurements"
              : `${data.latest_measurement.Appliances} Wh`
          }
        />
        <SummaryCard
          label="Latest measurement (local)"
          value={data.latest_timestamp?.replace("T", " ") ?? "No measurements"}
        />
        <SummaryCard label="Stored forecasts" value={data.prediction_count} />
      </div>
      <Panel title="Prediction readiness">
        <div data-dashboard-readiness={data.readiness.reason_code}>
          <p className="font-semibold">{readinessNames[data.readiness.reason_code]}</p>
          <p className="mt-2 text-sm">{data.readiness.message}</p>
          <p className="mt-2 text-xs text-muted-foreground">
            Required: {data.readiness.required_observations} observations at{" "}
            {data.readiness.required_interval_minutes}-minute intervals. Continuous latest history:{" "}
            {data.latest_timestamp ? data.readiness.continuous_intervals_available + 1 : 0}{" "}
            observations, capped at the required window.
          </p>
          {data.readiness.first_gap ? (
            <p className="mt-2 break-words text-sm">
              Gap: {data.readiness.first_gap.before_timestamp} to{" "}
              {data.readiness.first_gap.after_timestamp} (local).
            </p>
          ) : null}
        </div>
      </Panel>
      <DashboardForecast data={data} refreshing={query.isFetching} />
      <div>
        <label className="text-sm" htmlFor="energy-window">
          Measurement chart window
        </label>
        <select
          id="energy-window"
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="ml-3 rounded-md border bg-background p-2 text-sm"
        >
          <option value={144}>Latest 144 measurements</option>
          <option value={500}>Latest 500 measurements</option>
        </select>
      </div>
      <EnergyHistoryChart points={data.energy_history} total={data.measurement_count} />
      <Panel title="Recent persisted forecasts">
        <p className="mb-3 text-xs text-muted-foreground">
          Forecast history, not measured consumption. Newest saved first.
        </p>
        {data.recent_predictions.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr>
                  <th className="p-2">Forecast (local)</th>
                  <th>Predicted Wh</th>
                  <th>Level</th>
                  <th>Created (UTC)</th>
                  <th>Context</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_predictions.map((row) => (
                  <tr key={row.id} className="border-t" data-dashboard-prediction-id={row.id}>
                    <td className="whitespace-nowrap p-2">
                      {row.forecast_timestamp.replace("T", " ")}
                    </td>
                    <td>{row.prediction_wh.toFixed(3)}</td>
                    <td>{row.recommendation?.level ?? "Not stored"}</td>
                    <td className="whitespace-nowrap">{row.created_at.replace("T", " ")}</td>
                    <td>
                      {!query.isFetching && row.matches_current_history
                        ? "Matches current inputs"
                        : "Historical / checking"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>No prediction history yet.</p>
        )}
        <Link
          className="mt-3 inline-block text-sm underline"
          to="/predictions"
          search={{ building: String(selected.id) }}
        >
          Explore prediction history
        </Link>
        <Link
          className="ml-4 text-sm underline"
          to="/recommendations"
          search={{ building: String(selected.id) }}
        >
          View saved recommendations
        </Link>
      </Panel>
    </div>
  );
}
export function UserDashboard({
  selected,
  onSelect,
}: {
  selected: string | undefined;
  onSelect: (id: string) => void;
}) {
  return (
    <div data-user-dashboard className="space-y-5">
      <BuildingSelection selected={selected} onSelect={onSelect}>
        {(building) => <SelectedDashboard building={building} />}
      </BuildingSelection>
    </div>
  );
}
