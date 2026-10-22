import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { Panel } from "@/components/ui-kit";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/lib/auth";
export const Route = createFileRoute("/settings")({head: () => ({meta: [{title: "Account settings | SmartEnergyAI"}]}), component: SettingsPage});
function SettingsPage() {
  const { user } = useAuth();
  return <AppShell title="Settings" subtitle="Account information and local display preference"><div className="space-y-4">
    <Panel title="Appearance"><div className="flex items-center justify-between gap-4"><p className="text-sm text-muted-foreground">Choose the display theme for this browser.</p><ThemeToggle /></div></Panel>
    <Panel title="Account"><dl className="space-y-2 break-words text-sm"><dt>Name</dt><dd>{user?.full_name}</dd><dt>Email</dt><dd>{user?.email}</dd><dt>Role</dt><dd>{user?.role}</dd></dl><p className="mt-4 text-sm text-muted-foreground">Password changes, email delivery, verification and team invitations are unavailable.</p></Panel>
  </div></AppShell>;
}
