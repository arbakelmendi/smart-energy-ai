import { createFileRoute, Link } from "@tanstack/react-router";
import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
export const Route = createFileRoute("/login")({head: () => ({meta: [{title: "Prototype access | SmartEnergyAI"}, {name: "description", content: "The research dashboard is available without signing in."}]}), component: PrototypePage});
function PrototypePage() {
  return <AuthShell title="Prototype access" subtitle="The research dashboard is available without signing in.">
    <p className="text-sm text-muted-foreground">Research prototype only. No real authentication or account backend is operating. Do not enter real credentials.</p>
    <Button asChild variant="energy" className="mt-6 w-full"><Link to="/dashboard">Open research dashboard</Link></Button>
  </AuthShell>;
}
