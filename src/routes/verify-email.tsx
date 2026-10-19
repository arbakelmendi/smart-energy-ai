import { createFileRoute, Link } from "@tanstack/react-router";
import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
export const Route = createFileRoute("/verify-email")({head: () => ({meta: [{title: "Email verification unavailable | SmartEnergyAI"}, {name: "description", content: "No verification email has been sent. This prototype does not activate accounts."}]}), component: PrototypePage});
function PrototypePage() {
  return <AuthShell title="Email verification unavailable" subtitle="No verification email has been sent. This prototype does not activate accounts.">
    <p className="text-sm text-muted-foreground">Research prototype only. No real authentication or account backend is operating. Do not enter real credentials.</p>
    <Button asChild variant="energy" className="mt-6 w-full"><Link to="/dashboard">Open research dashboard</Link></Button>
  </AuthShell>;
}
