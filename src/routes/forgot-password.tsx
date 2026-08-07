import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { MailCheck } from "lucide-react";
import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const Route = createFileRoute("/forgot-password")({
  head: () => ({
    meta: [
      { title: "Reset your password — Smart Energy AI" },
      {
        name: "description",
        content: "Request a password reset link for your Smart Energy AI account.",
      },
      { property: "og:title", content: "Reset your password — Smart Energy AI" },
      { property: "og:description", content: "Request a secure reset link by email." },
    ],
  }),
  component: ForgotPasswordPage,
});

function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  return (
    <AuthShell
      title={sent ? "Check your inbox" : "Forgot your password?"}
      subtitle={
        sent
          ? `We sent a 6-digit code and a reset link to ${email}.`
          : "Enter the email tied to your account and we'll send a reset link."
      }
      footer={
        <>
          Remembered it?{" "}
          <Link to="/login" className="font-medium text-efficiency hover:underline">
            Back to login
          </Link>
        </>
      }
    >
      {sent ? (
        <div className="space-y-5">
          <div className="flex items-start gap-3 rounded-xl border border-efficiency/35 bg-efficiency/10 p-4">
            <MailCheck className="mt-0.5 size-5 shrink-0 text-efficiency" />
            <p className="text-sm text-muted-foreground">
              The link expires in 30 minutes. If it doesn't arrive, check spam or request a new one.
            </p>
          </div>
          <Button variant="energy" className="w-full" onClick={() => navigate({ to: "/reset-password" })}>
            I have the code — set a new password
          </Button>
          <Button variant="ghost" className="w-full" onClick={() => setSent(false)}>
            Use a different email
          </Button>
        </div>
      ) : (
        <form
          className="space-y-5"
          onSubmit={(e) => {
            e.preventDefault();
            if (!email.includes("@")) {
              toast.error("Enter a valid email address.");
              return;
            }
            setSent(true);
            toast.success("Reset instructions sent.");
          }}
        >
          <div className="space-y-2">
            <Label htmlFor="email">Account email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@organisation.org"
            />
          </div>
          <Button type="submit" variant="energy" size="lg" className="w-full">
            Send reset link
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
