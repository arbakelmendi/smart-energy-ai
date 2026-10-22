import { useEffect, useState, type FormEvent } from "react";
import { Panel } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import {
  useMeasurements,
  useCreateMeasurement,
  useDeleteMeasurement,
  useImportMeasurements,
} from "@/hooks/use-measurements";
import {
  rawFields,
  fieldUnit,
  type RawField,
  type CreateMeasurementRequest,
} from "@/lib/api/measurements";
import { ApiError } from "@/lib/api/client";

function MeasurementError({ error }: { error: Error | null }) {
  if (!error) return null;
  const payload = error instanceof ApiError ? error.detail : null;
  const detail =
    payload && typeof payload === "object" && "detail" in payload ? payload.detail : null;
  const details = Array.isArray(detail)
    ? (detail as { row?: number; field?: string; msg?: string }[])
    : [];
  return (
    <div role="alert" className="break-words text-sm text-destructive">
      <p>{error.message}</p>
      {details
        .filter((x) => x.row || x.field)
        .map((x, i) => (
          <p key={i}>
            CSV row {x.row ?? "header"}
            {x.field ? ` (${x.field})` : ""}: {x.msg}
          </p>
        ))}
    </div>
  );
}
const outdoor = [
  "T6",
  "RH_6",
  "T_out",
  "Press_mm_hg",
  "RH_out",
  "Windspeed",
  "Visibility",
  "Tdewpoint",
];
const groups = [
  { title: "Energy", fields: rawFields.filter((f) => f === "Appliances" || f === "lights") },
  {
    title: "Indoor conditions",
    fields: rawFields.filter((f) => !outdoor.includes(f) && f !== "Appliances" && f !== "lights"),
  },
  { title: "Outdoor / weather", fields: rawFields.filter((f) => outdoor.includes(f)) },
];
const inputClass = "w-full rounded-md border border-input bg-background px-3 py-2 text-sm";
const header = ["timestamp", ...rawFields].join(",");
function downloadHeader() {
  const url = URL.createObjectURL(new Blob([header + "\n"], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "measurement-header.csv";
  link.click();
  URL.revokeObjectURL(url);
}
function MeasurementForm({
  buildingId,
  onSaved,
  onCancel,
}: {
  buildingId: number;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const mutation = useCreateMeasurement(buildingId);
  const [hydrated, setHydrated] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  useEffect(() => setHydrated(true), []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    try {
      setError(null);
      const timestamp = String(values.get("timestamp"));
      const body = {
        timestamp: timestamp.length === 16 ? timestamp + ":00" : timestamp,
      } as CreateMeasurementRequest;
      for (const field of rawFields) {
        const value = String(values.get(field) ?? "");
        if (!value.trim() || !Number.isFinite(Number(value)))
          throw new Error(`${field} requires a finite number`);
        body[field] = Number(value);
      }
      await mutation.mutateAsync(body);
      form.reset();
      onSaved();
    } catch (error) {
      setError(error instanceof Error ? error : new Error("Measurement was not saved"));
    }
  }
  return (
    <form onSubmit={submit} method="post" className="space-y-4">
      <fieldset disabled={!hydrated || mutation.isPending} className="space-y-4">
        <legend className="mb-3 font-medium">Add measurement</legend>
        <label className="block text-sm">
          Timestamp (building-local, no timezone)
          <input className={inputClass} type="datetime-local" step="1" name="timestamp" required />
        </label>
        <p className="text-sm text-muted-foreground">
          All raw observations are required. Energy is Wh per observation interval; the reference
          dataset uses ten-minute intervals. Do not enter estimated defaults for unknown
          observations.
        </p>
        {groups.map((group) => (
          <fieldset key={group.title} className="rounded-md border p-3">
            <legend className="px-2 text-sm font-medium">{group.title}</legend>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {group.fields.map((field) => (
                <label key={field} className="text-sm">
                  {field} ({fieldUnit(field)})
                  <input className={inputClass} type="number" step="any" name={field} required />
                </label>
              ))}
            </div>
          </fieldset>
        ))}
        <MeasurementError error={error} />
        <div className="flex gap-3">
          <Button type="submit">
            {mutation.isPending ? "Saving measurement..." : "Save measurement"}
          </Button>
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancel measurement
          </Button>
        </div>
      </fieldset>
    </form>
  );
}
export function BuildingMeasurements({ buildingId }: { buildingId: number }) {
  const [offset, setOffset] = useState(0);
  const [adding, setAdding] = useState(false);
  const [confirm, setConfirm] = useState<number | null>(null);
  const query = useMeasurements(buildingId, 100, offset);
  const remove = useDeleteMeasurement(buildingId);
  const upload = useImportMeasurements(buildingId);
  const [localError, setLocalError] = useState<Error | null>(null);
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);
  async function importCsv(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const file = new FormData(form).get("file");
    upload.reset();
    setLocalError(null);
    if (!(file instanceof File) || !file.size) {
      setLocalError(new Error("Choose a nonempty CSV file"));
      return;
    }
    if (file.size > 16 * 1024 * 1024) {
      setLocalError(new Error("CSV exceeds 16 MiB limit"));
      return;
    }
    try {
      await upload.mutateAsync(file);
      setOffset(0);
      form.reset();
    } catch {
      /* Mutation error shown below. */
    }
  }
  const visible: RawField[] = ["Appliances", "lights", "T1", "RH_1", "T_out", "RH_out"];
  return (
    <Panel title="Measurements">
      <div className="space-y-5 min-w-0">
        <p className="text-sm text-muted-foreground">
          Stored raw observations. Prediction readiness is checked separately from the latest
          continuous history; a row count alone does not establish readiness or model validity
          for this building. Forecasts run only when explicitly requested.
        </p>
        {adding ? (
          <MeasurementForm
            buildingId={buildingId}
            onSaved={() => {
              setAdding(false);
              setOffset(0);
            }}
            onCancel={() => setAdding(false)}
          />
        ) : (
          <Button onClick={() => setAdding(true)}>Add measurement</Button>
        )}
        <form
          onSubmit={importCsv}
          method="post"
          encType="multipart/form-data"
          className="space-y-3 rounded-md border p-4"
        >
          <fieldset disabled={!hydrated || upload.isPending} className="space-y-3">
            <legend className="font-medium">Import CSV</legend>
            <label className="block text-sm">
              CSV file (UTF-8, maximum 16 MiB / 25,000 rows)
              <input
                className="mt-2 block max-w-full text-sm"
                type="file"
                name="file"
                accept=".csv,text/csv"
                required
              />
            </label>
            <p className="text-sm text-muted-foreground">
              All rows must validate before anything is saved. Duplicate timestamps reject the
              entire import. Use exactly date or timestamp plus the 26 raw fields; rv1/rv2 are
              ignored.
            </p>
            <details className="text-sm">
              <summary className="cursor-pointer">Expected CSV format and timestamp policy</summary>
              <p className="my-2">
                Use timezone-naive ISO date/time, for example YYYY-MM-DDTHH:mm:ss. UCI date strings
                also accept a space. Offsets and Z are rejected. Unknown columns are rejected.
              </p>
              <p className="break-all font-mono text-xs">{header}</p>
              <Button type="button" variant="wire" className="mt-2" onClick={downloadHeader}>
                Download header-only CSV
              </Button>
            </details>
            <Button type="submit">{upload.isPending ? "Importing CSV..." : "Upload CSV"}</Button>
          </fieldset>
          <MeasurementError error={localError ?? upload.error} />
          {upload.data ? (
            <div role="status" className="text-sm">
              <p>
                Imported {upload.data.rows_imported} of {upload.data.rows_received} rows.
              </p>
              <p>
                Range (local): {upload.data.first_timestamp} to {upload.data.last_timestamp}
              </p>
              {upload.data.ignored_columns.length ? (
                <p>Ignored: {upload.data.ignored_columns.join(", ")}</p>
              ) : null}
            </div>
          ) : null}
        </form>
        {query.isError ? (
          <div className="space-y-2">
            <MeasurementError error={query.error} />
            <Button
              onClick={() => {
                void query.refetch();
              }}
            >
              Retry measurements
            </Button>
          </div>
        ) : query.isPending ? (
          <p role="status">Loading measurements...</p>
        ) : (
          <>
            <div className="text-sm" data-measurement-count={query.data.total}>
              <p>Stored measurements: {query.data.total}</p>
              {query.data.first_timestamp ? (
                <p className="break-words">
                  Range (local): {query.data.first_timestamp} to {query.data.last_timestamp}
                </p>
              ) : null}
            </div>
            {query.data.total === 0 ? (
              <p className="text-sm">No measurements yet. Add an observation or import a CSV.</p>
            ) : (
              <>
                <div className="max-w-full overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr>
                        <th className="p-2">Timestamp (local)</th>
                        {visible.map((f) => (
                          <th className="p-2" key={f}>
                            {f} ({fieldUnit(f)})
                          </th>
                        ))}
                        <th className="p-2">Details / delete</th>
                      </tr>
                    </thead>
                    <tbody>
                      {query.data.items.map((row) => (
                        <tr className="border-t" key={row.id} data-measurement-id={row.id}>
                          <td className="whitespace-nowrap p-2">
                            {row.timestamp.replace("T", " ")}
                          </td>
                          {visible.map((f) => (
                            <td key={f} className="p-2">
                              {row[f]}
                            </td>
                          ))}
                          <td className="p-2">
                            <details>
                              <summary className="cursor-pointer">All fields</summary>
                              <dl>
                                {rawFields.map((f) => (
                                  <div key={f} className="whitespace-nowrap">
                                    <dt className="inline">{f}: </dt>
                                    <dd className="inline">
                                      {row[f]} {fieldUnit(f)}
                                    </dd>
                                  </div>
                                ))}
                              </dl>
                            </details>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                remove.reset();
                                setConfirm(row.id);
                              }}
                            >
                              Delete measurement
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {!query.data.items.length ? (
                  <p className="text-sm">
                    No rows on this page. Use Previous to return to stored history.
                  </p>
                ) : null}
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  <Button
                    variant="wire"
                    disabled={offset === 0}
                    onClick={() => setOffset(Math.max(0, offset - 100))}
                  >
                    Previous measurements
                  </Button>
                  <span>Offset {offset}; up to 100 rows</span>
                  <Button
                    variant="wire"
                    disabled={offset + 100 >= query.data.total}
                    onClick={() => setOffset(offset + 100)}
                  >
                    Next measurements
                  </Button>
                </div>
              </>
            )}
          </>
        )}
        {confirm !== null ? (
          <div className="space-y-3 rounded-md border p-4">
            <p className="text-sm">
              Delete this stored measurement permanently? This cannot be undone.
            </p>
            <MeasurementError error={remove.error} />
            <div className="flex gap-3">
              <Button
                variant="destructive"
                disabled={remove.isPending}
                onClick={async () => {
                  try {
                    await remove.mutateAsync(confirm);
                    setConfirm(null);
                    setOffset(0);
                  } catch {
                    /* Mutation error shown above. */
                  }
                }}
              >
                Confirm measurement delete
              </Button>
              <Button variant="ghost" disabled={remove.isPending} onClick={() => setConfirm(null)}>
                Cancel measurement delete
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    </Panel>
  );
}
