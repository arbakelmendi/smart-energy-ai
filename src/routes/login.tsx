import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { MetricPill } from "@/components/ui-kit";
import { demoCredentials, useAuth } from "@/lib/auth";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Log in — Smart Energy AI" },
      {
        name: "description",
        content: "Sign in to your Smart Energy AI control room to view forecasts and recommendations.",
      },
      { property: "og:title", content: "Log in — Smart Energy AI" },
      { property: "og:description", content: "Access your building energy forecasting dashboard." },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState(demoCredentials.email);
  const [password, setPassword] = useState(demoCredentials.password);
  const [remember, setRemember] = useState(true);
  const [busy, setBusy] = useState(false);

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to your energy control room."
      aside={
        <div className="mt-8 grid max-w-md grid-cols-3 gap-3">
          <MetricPill label="MAE" value="12.4" hint="kWh" />
          <MetricPill label="RMSE" value="18.9" hint="kWh" />
          <MetricPill label="R²" value="0.962" hint="held-out" />
        </div>
      }
      footer={
        <>
          No account yet?{" "}
          <Link to="/signup" className="font-medium text-efficiency hover:underline">
            Create one
          </Link>
        </>
      }
    >
      <form
        className="space-y-5"
        onSubmit={(e) => {
          e.preventDefault();
          if (!email.includes("@") || password.length < 6) {
            toast.error("Enter a valid email and a password of at least 6 characters.");
            return;
          }
          setBusy(true);
          signIn(email);
          toast.success("Signed in — loading telemetry.");
          navigate({ to: "/dashboard" });
        }}
      >
        <div className="space-y-2">
          <Label htmlFor="email">Work email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@organisation.org"
          />
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="password">Password</Label>
            <Link to="/forgot-password" className="text-xs text-efficiency hover:underline">
              Forgot password?
            </Link>
          </div>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <label className="flex items-center gap-2.5 text-sm text-muted-foreground">
          <Checkbox checked={remember} onCheckedChange={(v) => setRemember(Boolean(v))} />
          Remember me on this device
        </label>
        <Button type="submit" variant="energy" className="w-full" size="lg" disabled={busy}>
          {busy ? "Authenticating…" : "Sign in"}
        </Button>
        <p className="rounded-lg border border-border bg-surface-2/60 p-3 font-mono text-[11px] text-muted-foreground">
          demo account · {demoCredentials.email} / {demoCredentials.password}
        </p>
      </form>
    </AuthShell>
  );
}
