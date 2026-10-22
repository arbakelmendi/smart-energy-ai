import { createFileRoute } from "@tanstack/react-router";
import { AuthenticationForm } from "@/components/auth-form";
export const Route = createFileRoute("/signup")({
  head: () => ({ meta: [{ title: "Create account | SmartEnergyAI" }] }),
  component: () => <AuthenticationForm mode="signup" />,
});
