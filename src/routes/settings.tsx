import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { Monitor, Moon, Sun, UserPlus } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Panel } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";
import { platformUsers } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — Smart Energy AI" },
      {
        name: "description",
        content: "Manage your profile, password, notification preferences, theme and linked team accounts.",
      },
      { property: "og:title", content: "Settings — Smart Energy AI" },
      { property: "og:description", content: "Profile, notifications, theme and team management." },
    ],
  }),
  component: SettingsPage,
});

function SettingsPage() {
  const { user, update } = useAuth();
  const { theme, setTheme } = useTheme();
  const [name, setName] = useState(user?.name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [prefs, setPrefs] = useState({ anomaly: true, weekly: true, model: false, digest: true });

  return (
    <AppShell title="Settings" subtitle="Profile, notifications, appearance and team">
      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <div className="space-y-6">
          <Panel title="Personal information">
            <form
              className="space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                update({ name, email });
                toast.success("Profile updated.");
              }}
            >
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="sname">Full name</Label>
                  <Input id="sname" value={name} onChange={(e) => setName(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="semail">Email</Label>
                  <Input id="semail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Role: <span className="text-efficiency">{user?.role ?? "Viewer"}</span> — contact a
                platform admin to change it.
              </p>
              <Button type="submit" variant="energy" size="sm">Save changes</Button>
            </form>
          </Panel>

          <Panel title="Change password">
            <form
              className="grid gap-4 sm:grid-cols-3"
              onSubmit={(e) => {
                e.preventDefault();
                toast.success("Password changed.");
              }}
            >
              <div className="space-y-2">
                <Label htmlFor="cur">Current</Label>
                <Input id="cur" type="password" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="new1">New</Label>
                <Input id="new1" type="password" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="new2">Confirm</Label>
                <Input id="new2" type="password" />
              </div>
              <Button type="submit" variant="wire" size="sm" className="sm:col-span-3 sm:w-fit">
                Update password
              </Button>
            </form>
          </Panel>

          <Panel title="Linked team accounts" subtitle="people with access to your buildings">
            <ul className="divide-y divide-border">
              {platformUsers.slice(1, 5).map((u) => (
                <li key={u.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{u.name}</p>
                    <p className="truncate text-xs text-muted-foreground">{u.email}</p>
                  </div>
                  <span className="shrink-0 rounded-full border border-border px-2.5 py-0.5 text-[10px] uppercase">
                    {u.role}
                  </span>
                </li>
              ))}
            </ul>
            <Button variant="ghost" size="sm" className="mt-3" onClick={() => toast.success("Invitation sent.")}>
              <UserPlus className="size-3.5" /> Invite teammate
            </Button>
          </Panel>
        </div>

        <div className="space-y-6">
          <Panel title="Appearance" subtitle="dark is the default control-room theme">
            <div className="grid grid-cols-2 gap-3">
              {[
                { v: "dark" as const, icon: Moon, label: "Dark" },
                { v: "light" as const, icon: Sun, label: "Light" },
              ].map((t) => (
                <button
                  key={t.v}
                  onClick={() => setTheme(t.v)}
                  className={cn(
                    "rounded-xl border p-4 text-left transition-colors",
                    theme === t.v ? "border-efficiency/60 bg-efficiency/10" : "border-border hover:bg-muted",
                  )}
                >
                  <t.icon className="size-5 text-efficiency" />
                  <p className="mt-2 text-sm font-medium">{t.label}</p>
                </button>
              ))}
            </div>
            <p className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
              <Monitor className="size-3.5" /> Preference is stored per device.
            </p>
          </Panel>

          <Panel title="Notification preferences">
            <ul className="space-y-4">
              {[
                { k: "anomaly" as const, label: "Anomaly alerts", hint: "consumption outside the forecast band" },
                { k: "weekly" as const, label: "Weekly savings report", hint: "every Monday 08:00" },
                { k: "model" as const, label: "Model retraining events", hint: "when a new version is promoted" },
                { k: "digest" as const, label: "New recommendations", hint: "daily digest" },
              ].map((p) => (
                <li key={p.k} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
                  <div className="min-w-0">
                    <p className="text-sm">{p.label}</p>
                    <p className="text-xs text-muted-foreground">{p.hint}</p>
                  </div>
                  <Switch
                    checked={prefs[p.k]}
                    onCheckedChange={(v) => {
                      setPrefs((s) => ({ ...s, [p.k]: v }));
                      toast.success(`${p.label} ${v ? "enabled" : "disabled"}.`);
                    }}
                  />
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      </div>
    </AppShell>
  );
}
