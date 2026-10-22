import { createFileRoute } from "@tanstack/react-router";
import { AuthenticationForm } from "@/components/auth-form";
import { safeDestination } from "@/lib/auth-policy";
export const Route = createFileRoute("/login")({
  validateSearch: (search: Record<string, unknown>): { next?: string } => ({ next: safeDestination(search["next"]) }),
  head: () => ({ meta: [{ title: "Sign in | SmartEnergyAI" }] }),
  component: LoginPage,
});
function LoginPage() { const { next } = Route.useSearch(); return <AuthenticationForm mode="login" next={next} />; }
