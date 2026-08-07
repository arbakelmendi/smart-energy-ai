import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { Panel } from "@/components/ui-kit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { platformUsers, type PlatformUser } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/admin/users")({
  head: () => ({
    meta: [
      { title: "User management — Smart Energy AI" },
      {
        name: "description",
        content: "Platform admin console for reviewing accounts, roles and suspending or activating users.",
      },
      { property: "og:title", content: "User management — Smart Energy AI" },
      { property: "og:description", content: "Accounts, roles and account status control." },
    ],
  }),
  component: AdminUsers,
});

function AdminUsers() {
  const [users, setUsers] = useState<PlatformUser[]>(platformUsers);
  const [q, setQ] = useState("");
  const visible = users.filter((u) => `${u.name} ${u.email} ${u.role}`.toLowerCase().includes(q.toLowerCase()));

  const toggle = (id: string) =>
    setUsers((prev) =>
      prev.map((u) => {
        if (u.id !== id) return u;
        const status = u.status === "suspended" ? "active" : "suspended";
        toast.success(`${u.name} is now ${status}.`);
        return { ...u, status };
      }),
    );

  return (
    <AppShell title="User management" subtitle={`${users.length} accounts on this workspace`}>
      <Panel
        title="Accounts"
        bodyClassName="p-0"
        action={
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search users…"
            className="h-8 w-[220px] text-xs"
          />
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="border-b border-border text-left font-mono text-[10px] tracking-[0.16em] text-muted-foreground uppercase">
              <tr>
                <th className="px-5 py-3 font-medium">User</th>
                <th className="px-5 py-3 font-medium">Role</th>
                <th className="px-5 py-3 font-medium">Buildings</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Last seen</th>
                <th className="px-5 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((u) => (
                <tr key={u.id} className="border-b border-border/50 hover:bg-muted/40">
                  <td className="px-5 py-3">
                    <p className="font-medium">{u.name}</p>
                    <p className="text-xs text-muted-foreground">{u.email}</p>
                  </td>
                  <td className="px-5 py-3 text-xs">{u.role}</td>
                  <td className="stat-number px-5 py-3">{u.buildings}</td>
                  <td className="px-5 py-3">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                        u.status === "active"
                          ? "bg-efficiency/15 text-efficiency"
                          : u.status === "pending"
                            ? "bg-info/15 text-info"
                            : "bg-peak/15 text-peak",
                      )}
                    >
                      {u.status}
                    </span>
                  </td>
                  <td className="px-5 py-3 font-mono text-[11px] text-muted-foreground">{u.lastSeen}</td>
                  <td className="px-5 py-3">
                    <Button size="sm" variant="ghost" onClick={() => toggle(u.id)}>
                      {u.status === "suspended" ? "Activate" : "Suspend"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </AppShell>
  );
}
