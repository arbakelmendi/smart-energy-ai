import { createFileRoute, Link } from "@tanstack/react-router";
import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
export const Route = createFileRoute("/forgot-password")({head: () => ({meta: [{title: "Password recovery unavailable | SmartEnergyAI"}, {name: "description", content: "No authentication or email delivery service is connected. No reset email will be sent."}]}), component: PrototypePage});
function PrototypePage() {
  return <AuthShell title="Password recovery unavailable" subtitle="No authentication or email delivery service is connected. No reset email will be sent.">
    <p className="text-sm text-muted-foreground">Research prototype only. No real authentication or account backend is operating. Do not enter real credentials.</p>
    <Button asChild variant="energy" className="mt-6 w-full"><Link to="/dashboard">Open research dashboard</Link></Button>
  </AuthShell>;
}
