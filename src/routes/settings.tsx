import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { Panel } from "@/components/ui-kit";
import { ThemeToggle } from "@/components/theme-toggle";
export const Route = createFileRoute("/settings")({head: () => ({meta: [{title: "Prototype settings | SmartEnergyAI"}, {name: "description", content: "Local display preference; no account management service connected."}]}), component: SettingsPage});
function SettingsPage() {
  return <AppShell title="Prototype settings" subtitle="Local display preference only"><div className="space-y-4">
    <Panel title="Appearance"><div className="flex items-center justify-between gap-4"><p className="text-sm text-muted-foreground">Choose the display theme for this browser.</p><ThemeToggle /></div></Panel>
    <Panel title="Account services not connected"><p className="text-sm text-muted-foreground">Profiles, passwords, notifications and team invitations are not managed by a backend. No real account changes can be made here.</p></Panel>
  </div></AppShell>;
}
