import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { Panel } from "@/components/ui-kit";
export const Route = createFileRoute("/data")({ component: Page });
function Page() {
  return (
    <AppShell title="Measurement data" subtitle="Manual observations and CSV import">
      <Panel title="Manage measurements by building">
        <div className="space-y-3 text-sm">
          <p>
            Open an owned building to add all required raw observations, import a CSV, inspect real
            history, or delete a measurement.
          </p>
          <p>
            CSV imports are validated atomically. Timestamped records are not a live sensor feed.
            Readiness requires compatible continuous ten-minute history; stored count alone is
            insufficient.
          </p>
          <Link className="inline-block underline" to="/buildings">
            Open Buildings
          </Link>
          <Link className="ml-4 underline" to="/dashboard">
            Open dashboard
          </Link>
        </div>
      </Panel>
    </AppShell>
  );
}
