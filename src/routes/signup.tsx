import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth, type Role } from "@/lib/auth";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/signup")({
  head: () => ({
    meta: [
      { title: "Create account — Smart Energy AI" },
      {
        name: "description",
        content:
          "Create a Smart Energy AI account as Building Admin, Analyst or Viewer and start forecasting consumption.",
      },
      { property: "og:title", content: "Create account — Smart Energy AI" },
      {
        property: "og:description",
        content: "Join the pilot: ML forecasting and optimization for smart buildings.",
      },
    ],
  }),
  component: SignupPage,
});

const roles: Array<{ value: Role; label: string; text: string }> = [
  {
    value: "Building Admin",
    label: "Building Admin",
    text: "Manage buildings, data sources and apply recommendations.",
  },
  { value: "Analyst", label: "Analyst", text: "Explore models, metrics and export reports." },
  { value: "Viewer", label: "Viewer", text: "Read-only access to dashboards and alerts." },
];

function SignupPage() {
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("Building Admin");

  return (
    <AuthShell
      title="Create your account"
      subtitle="Two minutes to your first forecast."
      footer={
        <>
          Already registered?{" "}
          <Link to="/login" className="font-medium text-efficiency hover:underline">
            Log in
          </Link>
        </>
      }
    >
      <form
        className="space-y-5"
        onSubmit={(e) => {
          e.preventDefault();
          if (!name.trim() || !email.includes("@") || password.length < 8) {
            toast.error("Full name, a valid email and an 8+ character password are required.");
            return;
          }
          signUp(name.trim(), email.trim(), role);
          toast.success("Account created — verify your email to continue.");
          navigate({ to: "/verify-email" });
        }}
      >
        <div className="space-y-2">
          <Label htmlFor="name">Full name</Label>
          <Input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Elira Hoxha" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">Work email</Label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@organisation.org"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters"
          />
        </div>
        <fieldset className="space-y-2">
          <legend className="mb-2 text-sm font-medium">Account role</legend>
          <div className="space-y-2">
            {roles.map((r) => (
              <button
                key={r.value}
                type="button"
                onClick={() => setRole(r.value)}
                className={cn(
                  "w-full rounded-xl border p-3.5 text-left transition-colors",
                  role === r.value
                    ? "border-efficiency/60 bg-efficiency/10"
                    : "border-border hover:bg-muted",
                )}
              >
                <span className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium">{r.label}</span>
                  <span
                    className={cn(
                      "size-3.5 rounded-full border",
                      role === r.value ? "border-efficiency bg-efficiency" : "border-border",
                    )}
                  />
                </span>
                <span className="mt-1 block text-xs text-muted-foreground">{r.text}</span>
              </button>
            ))}
          </div>
        </fieldset>
        <Button type="submit" variant="energy" size="lg" className="w-full">
          Create account
        </Button>
      </form>
    </AuthShell>
  );
}
