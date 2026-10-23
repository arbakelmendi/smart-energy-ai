import { createFileRoute, Link } from "@tanstack/react-router";
import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
export const Route = createFileRoute("/forgot-password")({head: () => ({meta: [{title: "Password recovery unavailable | SmartEnergyAI"}, {name: "description", content: "No password recovery or email delivery service is connected. No reset email will be sent."}]}), component: PrototypePage});
function PrototypePage() {
  return <AuthShell title="Password recovery unavailable" subtitle="No password recovery or email delivery service is connected. No reset email will be sent.">
    <p className="text-sm text-muted-foreground">This service is not implemented. Existing accounts can sign in; no email delivery or building setup action is performed here.</p>
    <Button asChild variant="energy" className="mt-6 w-full"><Link to="/dashboard">Open research dashboard</Link></Button>
  </AuthShell>;
}
