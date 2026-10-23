import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Panel } from "@/components/ui-kit";
import { AdminState, AdminPagination } from "@/components/admin-common";
import { useAdminOverview, useAdminPredictions } from "@/hooks/use-admin";
function PredictionActivity() {
  const [offset, setOffset] = useState(0);
  const query = useAdminPredictions(offset);
  return (
    <Panel
      title="Persisted prediction activity"
      subtitle="Forecast history across owners; not measured consumption or a login audit log"
    >
      <AdminState
        pending={query.isPending}
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      >
        {query.data ? (
          <>
            {!query.data.items.length ? (
              <p>No saved predictions on this page.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[950px] text-left text-sm">
                  <thead>
                    <tr>
                      {[
                        "Owner",
                        "Building",
                        "Source / Forecast (local)",
                        "Predicted Wh",
                        "Level",
                        "Created (UTC)",
                      ].map((label) => (
                        <th className="p-3" key={label}>
                          {label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {query.data.items.map((row) => (
                      <tr className="border-t" key={row.id} data-admin-prediction={row.id}>
                        <td className="p-3">
                          <Link
                            to="/admin/users"
                            search={{ user: String(row.owner.id) }}
                            className="underline"
                          >
                            {row.owner.full_name}
                          </Link>
                          <p>{row.owner.email}</p>
                        </td>
                        <td className="p-3">
                          <Link
                            to="/admin/buildings"
                            search={{ building: String(row.building_id) }}
                            className="underline"
                          >
                            {row.building_name}
                          </Link>
                        </td>
                        <td className="whitespace-nowrap p-3">
                          {row.source_timestamp.replace("T", " ")}
                          <br />
                          {row.forecast_timestamp.replace("T", " ")}
                        </td>
                        <td className="p-3">{row.prediction_wh.toFixed(3)}</td>
                        <td className="p-3">{row.recommendation_level ?? "Not stored"}</td>
                        <td className="whitespace-nowrap p-3">
                          {row.created_at.replace("T", " ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <AdminPagination offset={offset} total={query.data.total} onChange={setOffset} />
          </>
        ) : null}
      </AdminState>
    </Panel>
  );
}
export function AdminOverview() {
  const query = useAdminOverview();
  const labels = {
    total_users: "Users",
    active_users: "Active users",
    inactive_users: "Inactive users",
    admin_users: "Administrators",
    regular_users: "Regular users",
    total_buildings: "Buildings",
    total_measurements: "Measurements",
    total_predictions: "Predictions",
  };
  return (
    <div className="space-y-5" data-admin-overview>
      <p className="text-sm text-muted-foreground">
        Application-wide database counts. Measurements are manually entered or CSV imported; these
        counts do not indicate online sensors, validated building accuracy or savings.
      </p>
      <AdminState
        pending={query.isPending}
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      >
        {query.data ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {(Object.keys(labels) as (keyof typeof labels)[]).map((key) => (
              <div className="panel p-5" key={key}>
                <p className="text-sm text-muted-foreground">{labels[key]}</p>
                <p className="mt-2 text-2xl font-semibold" data-admin-count={key}>
                  {query.data[key]}
                </p>
              </div>
            ))}
          </div>
        ) : null}
      </AdminState>
      <PredictionActivity />
    </div>
  );
}
