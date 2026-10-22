import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Panel } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import { BuildingPredictions } from "@/components/building-predictions";
import { PredictionReadinessPanel } from "@/components/prediction-readiness";
import { BuildingMeasurements } from "@/components/building-measurements";
import { BuildingForm } from "@/components/building-form";
import { useBuilding, useBuildings, useCreateBuilding, useDeleteBuilding, useUpdateBuilding } from "@/hooks/use-buildings";
import { ApiError } from "@/lib/api/client";
import { parseBuildingId, type Building } from "@/lib/api/buildings";

function BuildingError({ error, retry }: { error: Error; retry: () => void }) {
  const missing = error instanceof ApiError && error.status === 404;
  return <Panel title={missing ? "Building not found" : "Building data unavailable"}><div role="alert" className="space-y-3 text-sm">
    <p>{missing ? "This building does not exist or is not owned by your account." : error.message}</p>
    {!missing ? <Button onClick={retry}>Retry buildings</Button> : null}<Link to="/buildings" className="ml-3 underline">All buildings</Link>
  </div></Panel>;
}
export function BuildingsList() {
  const query = useBuildings(); const create = useCreateBuilding(); const navigate = useNavigate();
  const [adding, setAdding] = useState(false);
  return <div className="space-y-5">
    <p className="text-sm text-muted-foreground">Buildings owned by your account. Creating a building does not establish model validity for it.</p>
    {adding ? <Panel title="Add building"><BuildingForm pending={create.isPending} error={create.error} onCancel={() => {setAdding(false);create.reset();}}
      onSave={async body => { const building = await create.mutateAsync(body); await navigate({to:"/buildings/$id",params:{id:String(building.id)}}); }} /></Panel>
      : <Button variant="energy" onClick={() => {create.reset();setAdding(true);}}>Add building</Button>}
    {query.isError ? <BuildingError error={query.error} retry={() => {void query.refetch();}} /> : query.isPending ? <p role="status">Loading buildings...</p> : query.data.buildings.length === 0 ?
      <Panel title="No buildings yet"><p className="text-sm text-muted-foreground">Add a building to store metadata and raw measurement history.</p></Panel> :
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{query.data.buildings.map(building => <Link key={building.id} to="/buildings/$id" params={{id:String(building.id)}} className="panel lift min-w-0 space-y-2 break-words p-5">
        <h2 className="font-semibold">{building.name}</h2><p className="text-sm text-muted-foreground">{building.building_type ?? "Type not specified"}</p>
        <p className="text-sm">{building.city ?? "City not specified"}</p><p className="text-sm">{building.floor_area_m2 === null ? "Area not specified" : `${building.floor_area_m2} m2`}</p>
      </Link>)}</div>}
  </div>;
}
export function BuildingDetailContent({ value }: { value: string }) {
  const id = parseBuildingId(value); const query = useBuilding(id);
  if (id === null) return <BuildingError error={new ApiError("Building not found",404)} retry={() => {}} />;
  if (query.isError) return <BuildingError error={query.error} retry={() => {void query.refetch();}} />;
  if (query.isPending) return <p role="status">Loading building...</p>;
  return <PersistedBuilding key={query.data.id} building={query.data} />;
}
function PersistedBuilding({ building }: { building: Building }) {
  const [editing,setEditing] = useState(false); const [confirming,setConfirming] = useState(false);
  const update = useUpdateBuilding(building.id); const remove = useDeleteBuilding(building.id); const navigate = useNavigate();
  return <div className="space-y-5">
    <div className="flex flex-wrap gap-4"><Link to="/buildings" className="text-sm underline">All buildings</Link><Link to="/dashboard" search={{building:String(building.id)}} className="text-sm underline">Open building dashboard</Link></div>
    {editing ? <Panel title="Edit building"><BuildingForm initial={building} pending={update.isPending} error={update.error}
      onCancel={() => {setEditing(false);update.reset();}} onSave={async body => {await update.mutateAsync(body);setEditing(false);}} /></Panel> :
      <Panel title="Building overview"><dl className="grid gap-3 break-words text-sm sm:grid-cols-2">
        <div><dt className="text-muted-foreground">Name</dt><dd>{building.name}</dd></div><div><dt className="text-muted-foreground">Type</dt><dd>{building.building_type ?? "Not specified"}</dd></div>
        <div><dt className="text-muted-foreground">Floor area</dt><dd>{building.floor_area_m2 === null ? "Not specified" : `${building.floor_area_m2} m2`}</dd></div><div><dt className="text-muted-foreground">City</dt><dd>{building.city ?? "Not specified"}</dd></div>
        <div className="sm:col-span-2"><dt className="text-muted-foreground">Description</dt><dd className="whitespace-pre-wrap">{building.description || "Not provided"}</dd></div>
        <div><dt className="text-muted-foreground">Created (UTC)</dt><dd>{building.created_at.replace("T"," ")}</dd></div><div><dt className="text-muted-foreground">Updated (UTC)</dt><dd>{building.updated_at.replace("T"," ")}</dd></div>
      </dl><div className="mt-5 flex flex-wrap gap-3"><Button variant="wire" onClick={() => {update.reset();setEditing(true);setConfirming(false);}}>Edit building</Button><Button variant="ghost" className="text-destructive" onClick={() => {remove.reset();setConfirming(true);}}>Delete building</Button></div></Panel>}
    {confirming ? <Panel title="Delete this building?"><p className="text-sm">Deleting this building permanently removes its metadata and any associated measurement and prediction history stored now or in the future. This cannot be undone.</p>
      {remove.error ? <p role="alert" className="mt-3 text-sm text-destructive">{remove.error.message}</p> : null}
      <div className="mt-4 flex gap-3"><Button variant="destructive" disabled={remove.isPending} onClick={async () => {try {await remove.mutateAsync();await navigate({to:"/buildings"});} catch {/* Error is shown by mutation state. */}}}>{remove.isPending ? "Deleting..." : "Confirm delete"}</Button><Button variant="ghost" disabled={remove.isPending} onClick={() => setConfirming(false)}>Cancel delete</Button></div></Panel> : null}
    <PredictionReadinessPanel buildingId={building.id} />
    <BuildingPredictions buildingId={building.id} />
    <BuildingMeasurements buildingId={building.id} />
  </div>;
}
