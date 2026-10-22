import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { buildingTypes, type Building, type CreateBuildingRequest } from "@/lib/api/buildings";

export function BuildingForm({ initial, pending, error, onSave, onCancel }: {
  initial?: Building; pending: boolean; error: Error | null;
  onSave: (body: CreateBuildingRequest) => Promise<void>; onCancel: () => void;
}) {
  const [hydrated, setHydrated] = useState(false);
  const [validation, setValidation] = useState("");
  useEffect(() => setHydrated(true), []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const fields = new FormData(event.currentTarget);
    const name = String(fields.get("name") ?? "").trim();
    const areaText = String(fields.get("floor_area_m2") ?? "").trim();
    const area = areaText ? Number(areaText) : null;
    if (!name) { setValidation("Enter a building name."); return; }
    if (area !== null && (!Number.isFinite(area) || area <= 0)) { setValidation("Floor area must be finite and greater than zero."); return; }
    setValidation("");
    const type = String(fields.get("building_type") ?? "");
    const body: CreateBuildingRequest = { name, building_type: type ? type as typeof buildingTypes[number] : null,
      floor_area_m2: area, city: String(fields.get("city") ?? "").trim() || null, description: String(fields.get("description") ?? "") || null };
    try { await onSave(body); } catch { /* Mutation state reports the server error; keep entered values. */ }
  }
  return <form method="post" onSubmit={submit}><fieldset disabled={!hydrated || pending} className="min-w-0 space-y-4">
    <label className="block text-sm">Name (required)<Input name="name" required maxLength={200} defaultValue={initial?.name ?? ""} className="mt-2" /></label>
    <label className="block text-sm">Building type (optional)<select name="building_type" defaultValue={initial?.building_type ?? ""} className="mt-2 h-9 w-full rounded-md border border-input bg-background px-3"><option value="">Not specified</option>{buildingTypes.map(type => <option key={type}>{type}</option>)}</select></label>
    <label className="block text-sm">Floor area in m2 (optional)<Input name="floor_area_m2" type="number" min="0" step="any" defaultValue={initial?.floor_area_m2 ?? ""} className="mt-2" /></label>
    <label className="block text-sm">City (optional)<Input name="city" maxLength={200} defaultValue={initial?.city ?? ""} className="mt-2" /></label>
    <label className="block text-sm">Description (optional)<textarea name="description" maxLength={4000} defaultValue={initial?.description ?? ""} rows={4} className="mt-2 w-full rounded-md border border-input bg-background p-3" /></label>
    {validation || error ? <p role="alert" className="break-words text-sm text-destructive">{validation || error?.message}</p> : null}
    <div className="flex gap-3"><Button type="submit" variant="energy">{pending ? "Saving..." : "Save building"}</Button><Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button></div>
  </fieldset></form>;
}
