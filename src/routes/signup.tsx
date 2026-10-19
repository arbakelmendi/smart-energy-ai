import { createFileRoute, Link } from "@tanstack/react-router";
import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
export const Route = createFileRoute("/signup")({head: () => ({meta: [{title: "Account creation unavailable | SmartEnergyAI"}, {name: "description", content: "No account service is connected. No registration is performed."}]}), component: PrototypePage});
function PrototypePage() {
  return <AuthShell title="Account creation unavailable" subtitle="No account service is connected. No registration is performed.">
    <p className="text-sm text-muted-foreground">Research prototype only. No real authentication or account backend is operating. Do not enter real credentials.</p>
    <Button asChild variant="energy" className="mt-6 w-full"><Link to="/dashboard">Open research dashboard</Link></Button>
  </AuthShell>;
}
