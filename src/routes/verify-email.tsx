import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { MailCheck, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/verify-email")({
  head: () => ({
    meta: [
      { title: "Verify your email — Smart Energy AI" },
      {
        name: "description",
        content: "Confirm your email address to activate your Smart Energy AI account.",
      },
      { property: "og:title", content: "Verify your email — Smart Energy AI" },
      { property: "og:description", content: "One click to activate your account." },
    ],
  }),
  component: VerifyEmailPage,
});

function VerifyEmailPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <AuthShell
      title="Verify your email"
      subtitle={`We sent a confirmation link to ${user?.email ?? "your inbox"}.`}
      footer={
        <>
          Wrong address?{" "}
          <Link to="/signup" className="font-medium text-efficiency hover:underline">
            Sign up again
          </Link>
        </>
      }
    >
      <div className="space-y-5">
        <div className="flex items-start gap-3 rounded-xl border border-efficiency/35 bg-efficiency/10 p-4">
          <MailCheck className="mt-0.5 size-5 shrink-0 text-efficiency" />
          <p className="text-sm text-muted-foreground">
            Verification keeps building telemetry tied to a real operator. The link is valid for 24
            hours.
          </p>
        </div>
        <Button variant="energy" size="lg" className="w-full" onClick={() => navigate({ to: "/onboarding" })}>
          I've verified — continue to setup
        </Button>
        <Button
          variant="outline"
          className="w-full"
          onClick={() => toast.success("Verification email re-sent.")}
        >
          <RefreshCw className="size-4" /> Resend email
        </Button>
        <p className="font-mono text-[11px] text-muted-foreground">
          demo mode · no email is actually dispatched
        </p>
      </div>
    </AuthShell>
  );
}
