import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Panel } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { buildingTypes } from "@/lib/api/buildings";
import { adminSelectedId } from "@/lib/admin-view";
import type { AdminBuildingFilters } from "@/lib/api/admin";
import { useAdminBuilding, useAdminBuildings } from "@/hooks/use-admin";
import { AdminState, AdminPagination, AdminBuildingsTable } from "@/components/admin-common";
function BuildingDetail({ id }: { id: number }) {
  const query = useAdminBuilding(id);
  return (
    <div className="space-y-5">
      <Link to="/admin/buildings" search={{}} className="underline">
        Back to all buildings
      </Link>
      <AdminState
        pending={query.isPending}
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      >
        {query.data ? (
          <Panel title={query.data.name}>
            <div
              className="space-y-3 break-words text-sm"
              data-admin-building-detail={query.data.id}
            >
              <p>
                Owner:{" "}
                <Link
                  to="/admin/users"
                  search={{ user: String(query.data.owner.id) }}
                  className="underline"
                >
                  {query.data.owner.full_name} | {query.data.owner.email}
                </Link>
              </p>
              <p>
                {query.data.building_type ?? "Type not specified"} |{" "}
                {query.data.city ?? "City not specified"} | Area:{" "}
                {query.data.floor_area_m2 === null
                  ? "Not specified"
                  : `${query.data.floor_area_m2} m2`}
              </p>
              <p className="whitespace-pre-wrap">
                {query.data.description ?? "No description stored"}
              </p>
              <p>Created (UTC): {query.data.created_at.replace("T", " ")}</p>
              <p>
                Measurements: {query.data.measurement_count} | Predictions:{" "}
                {query.data.prediction_count}
              </p>
              <p>
                Measurement range (local):{" "}
                {query.data.earliest_measurement_timestamp?.replace("T", " ") ?? "No measurements"}{" "}
                to {query.data.latest_measurement_timestamp?.replace("T", " ") ?? "No measurements"}
              </p>
              {query.data.latest_prediction ? (
                <div className="rounded-md border p-4">
                  <p>Latest saved prediction, not necessarily current:</p>
                  <p>
                    Source (local):{" "}
                    {query.data.latest_prediction.source_timestamp.replace("T", " ")}
                  </p>
                  <p>
                    Forecast (local):{" "}
                    {query.data.latest_prediction.forecast_timestamp.replace("T", " ")}
                  </p>
                  <p>
                    {query.data.latest_prediction.prediction_wh.toFixed(3)} Wh |{" "}
                    {query.data.latest_prediction.recommendation_level ??
                      "No recommendation snapshot"}
                  </p>
                  <p>Saved (UTC): {query.data.latest_prediction.created_at.replace("T", " ")}</p>
                </div>
              ) : (
                <p>No saved prediction.</p>
              )}
              <p className="text-xs text-muted-foreground">
                Read-only oversight. Cross-owner measurement editing, forecasting and building
                deletion are unavailable here. Metadata is application context, not a model input.
                Forecasts outside the original UCI validation domain remain experimental.
              </p>
            </div>
          </Panel>
        ) : null}
      </AdminState>
    </div>
  );
}
function BuildingsList() {
  const [filters, setFilters] = useState<AdminBuildingFilters>({ limit: 50, offset: 0 });
  const query = useAdminBuildings(filters);
  return (
    <Panel title="Cross-owner building inventory">
      <form
        className="mb-5 flex flex-wrap gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          const data = new FormData(e.currentTarget);
          const owner = String(data.get("owner"));
          const type = String(data.get("type"));
          setFilters({
            limit: 50,
            offset: 0,
            search: String(data.get("search")),
            ...(owner ? { owner_id: Number(owner) } : {}),
            ...(type ? { building_type: type } : {}),
          });
        }}
      >
        <Input
          name="search"
          aria-label="Search buildings"
          placeholder="Building name or city"
          className="w-full sm:w-64"
        />
        <Input
          name="owner"
          aria-label="Owner ID"
          type="number"
          min="1"
          step="1"
          placeholder="Owner ID"
          className="w-full sm:w-36"
        />
        <select
          name="type"
          aria-label="Building type"
          className="rounded-md border bg-background p-2"
        >
          <option value="">All types</option>
          {buildingTypes.map((type) => (
            <option key={type}>{type}</option>
          ))}
        </select>
        <Button type="submit">Search buildings</Button>
      </form>
      <AdminState
        pending={query.isPending}
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      >
        {query.data ? (
          <>
            <AdminBuildingsTable items={query.data.items} />
            <AdminPagination
              total={query.data.total}
              offset={filters.offset ?? 0}
              onChange={(offset) => setFilters({ ...filters, offset })}
            />
          </>
        ) : null}
      </AdminState>
    </Panel>
  );
}
export function AdminBuildings({ selected }: { selected: string | undefined }) {
  const id = adminSelectedId(selected);
  if (selected !== undefined && id === null)
    return (
      <Panel title="Invalid building selection">
        <Link to="/admin/buildings" search={{}} className="underline">
          Back to all buildings
        </Link>
      </Panel>
    );
  return id === null ? <BuildingsList /> : <BuildingDetail key={id} id={id} />;
}
