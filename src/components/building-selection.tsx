import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { useBuildings } from "@/hooks/use-buildings";
import { Panel } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import { selectedOwnedBuilding } from "@/lib/dashboard-view";
import type { Building } from "@/lib/api/buildings";
import { useAuth } from "@/lib/auth";
export function BuildingSelection({
  selected,
  onSelect,
  children,
}: {
  selected: string | undefined;
  onSelect: (id: string) => void;
  children: (building: Building) => ReactNode;
}) {
  const query = useBuildings();
  const { user } = useAuth();
  if (query.isError)
    return (
      <Panel title="Buildings unavailable">
        <p role="alert">{query.error.message}</p>
        <Button
          onClick={() => {
            void query.refetch();
          }}
        >
          Retry buildings
        </Button>
      </Panel>
    );
  if (query.isPending) return <p role="status">Loading your buildings...</p>;
  const buildings = query.data.buildings;
  const building = selectedOwnedBuilding(buildings, selected);
  return (
    <div className="space-y-5">
      <Panel title="Selected building">
        <label className="block text-sm" htmlFor="building-selector">
          Your building
        </label>
        <select
          id="building-selector"
          className="mt-2 w-full rounded-md border border-input bg-background p-3 text-sm"
          value={building ? String(building.id) : ""}
          onChange={(e) => onSelect(e.target.value)}
        >
          <option value="" disabled>
            Choose an owned building
          </option>
          {buildings.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
              {b.building_type ? ` | ${b.building_type}` : ""}
              {b.city ? ` | ${b.city}` : ""}
            </option>
          ))}
        </select>
        <Link to="/buildings" className="mt-3 inline-block text-sm underline">
          Manage your buildings
        </Link>
      </Panel>
      {building ? (
        <div key={`${user?.id}:${building.id}`} data-selected-building={building.id}>
          {children(building)}
        </div>
      ) : (
        <Panel title={selected !== undefined ? "Building unavailable" : "No buildings yet"}>
          <p className="text-sm">
            {selected !== undefined
              ? "This building is not available in your account. Choose an owned building or open Buildings."
              : "Create your first building to start storing measurements."}
          </p>
          <Link to="/buildings" className="mt-3 inline-block text-sm underline">
            Open Buildings
          </Link>
        </Panel>
      )}
    </div>
  );
}
