import { createFileRoute, Link } from "@tanstack/react-router";
import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
export const Route = createFileRoute("/reset-password")({head: () => ({meta: [{title: "Password reset unavailable | SmartEnergyAI"}, {name: "description", content: "No account password can be changed in this prototype."}]}), component: PrototypePage});
function PrototypePage() {
  return <AuthShell title="Password reset unavailable" subtitle="No account password can be changed in this prototype.">
    <p className="text-sm text-muted-foreground">This service is not implemented. Existing accounts can sign in; no email delivery or building setup action is performed here.</p>
    <Button asChild variant="energy" className="mt-6 w-full"><Link to="/dashboard">Open research dashboard</Link></Button>
  </AuthShell>;
}
