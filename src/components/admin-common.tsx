import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { Panel } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import type { AdminBuilding } from "@/lib/api/admin";
export function AdminState({
  pending,
  error,
  retry,
  children,
}: {
  pending: boolean;
  error: Error | null;
  retry: () => void;
  children: ReactNode;
}) {
  if (error)
    return (
      <Panel title="Administration unavailable">
        <p role="alert">{error.message}</p>
        <Button onClick={retry}>Retry administration</Button>
      </Panel>
    );
  if (pending) return <p role="status">Loading persisted administration data...</p>;
  return <>{children}</>;
}
export function AdminPagination({
  offset,
  total,
  onChange,
}: {
  offset: number;
  total: number;
  onChange: (offset: number) => void;
}) {
  return (
    <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
      <Button
        variant="wire"
        disabled={offset === 0}
        onClick={() => onChange(Math.max(0, offset - 50))}
      >
        Previous page
      </Button>
      <span>
        Offset {offset} | {total} matching records
      </span>
      <Button variant="wire" disabled={offset + 50 >= total} onClick={() => onChange(offset + 50)}>
        Next page
      </Button>
    </div>
  );
}
export function AdminBuildingsTable({ items }: { items: AdminBuilding[] }) {
  if (!items.length) return <p>No matching buildings.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[850px] text-left text-sm">
        <thead>
          <tr>
            {[
              "Building",
              "Owner",
              "Type / City",
              "Measurements",
              "Predictions",
              "Created (UTC)",
            ].map((label) => (
              <th key={label} className="p-3">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((row) => (
            <tr key={row.id} className="border-t" data-admin-building={row.id}>
              <td className="p-3">
                <Link
                  className="underline"
                  to="/admin/buildings"
                  search={{ building: String(row.id) }}
                >
                  {row.name}
                </Link>
              </td>
              <td className="p-3">
                <Link
                  className="underline"
                  to="/admin/users"
                  search={{ user: String(row.owner.id) }}
                >
                  {row.owner.full_name}
                </Link>
                <p>{row.owner.email}</p>
              </td>
              <td className="p-3">
                {row.building_type ?? "Not specified"}
                <br />
                {row.city ?? "Not specified"}
              </td>
              <td className="p-3">{row.measurement_count}</td>
              <td className="p-3">{row.prediction_count}</td>
              <td className="whitespace-nowrap p-3">{row.created_at.replace("T", " ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
