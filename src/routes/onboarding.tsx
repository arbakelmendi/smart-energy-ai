import { createFileRoute, Link } from "@tanstack/react-router";
import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
export const Route = createFileRoute("/onboarding")({head: () => ({meta: [{title: "Building setup | SmartEnergyAI"}, {name: "description", content: "Create owned building metadata in Buildings, then add manual measurements or import CSV history. Live sensor connections are not provided."}]}), component: PrototypePage});
function PrototypePage() {
  return <AuthShell title="Building setup" subtitle="Create owned building metadata in Buildings, then add manual measurements or import CSV history. Live sensor connections are not provided.">
    <p className="text-sm text-muted-foreground">Sign in to manage your own buildings. Creating metadata does not establish model validity for a building or connect a live sensor feed.</p>
    <Button asChild variant="energy" className="mt-6 w-full"><Link to="/buildings">Open Buildings</Link></Button>
  </AuthShell>;
}
