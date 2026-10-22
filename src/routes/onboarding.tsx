import { createFileRoute, Link } from "@tanstack/react-router";
import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
export const Route = createFileRoute("/onboarding")({head: () => ({meta: [{title: "Building setup unavailable | SmartEnergyAI"}, {name: "description", content: "No building registration or live sensor connection is available. No setup action is performed."}]}), component: PrototypePage});
function PrototypePage() {
  return <AuthShell title="Building setup unavailable" subtitle="No building registration or live sensor connection is available. No setup action is performed.">
    <p className="text-sm text-muted-foreground">This service is not implemented. Existing accounts can sign in; no email delivery or building setup action is performed here.</p>
    <Button asChild variant="energy" className="mt-6 w-full"><Link to="/dashboard">Open research dashboard</Link></Button>
  </AuthShell>;
}
