import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const Route = createFileRoute("/reset-password")({
  head: () => ({
    meta: [
      { title: "Set a new password — Smart Energy AI" },
      {
        name: "description",
        content: "Enter your reset code and choose a new password for Smart Energy AI.",
      },
      { property: "og:title", content: "Set a new password — Smart Energy AI" },
      { property: "og:description", content: "Complete your password reset securely." },
    ],
  }),
  component: ResetPasswordPage,
});

function ResetPasswordPage() {
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");

  const strength = Math.min(
    100,
    pw.length * 8 + (/[A-Z]/.test(pw) ? 15 : 0) + (/\d/.test(pw) ? 15 : 0) + (/[^\w]/.test(pw) ? 15 : 0),
  );

  return (
    <AuthShell title="Choose a new password" subtitle="Paste the 6-digit code from your email.">
      <form
        className="space-y-5"
        onSubmit={(e) => {
          e.preventDefault();
          if (code.replace(/\D/g, "").length !== 6) {
            toast.error("The reset code must be 6 digits.");
            return;
          }
          if (pw.length < 8 || pw !== pw2) {
            toast.error("Passwords must match and be at least 8 characters.");
            return;
          }
          toast.success("Password updated — you can sign in now.");
          navigate({ to: "/login" });
        }}
      >
        <div className="space-y-2">
          <Label htmlFor="code">Reset code</Label>
          <Input
            id="code"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="482913"
            className="font-mono tracking-[0.4em]"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="pw">New password</Label>
          <Input id="pw" type="password" value={pw} onChange={(e) => setPw(e.target.value)} />
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-efficiency transition-[width] duration-300"
              style={{ width: `${strength}%` }}
            />
          </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="pw2">Confirm password</Label>
          <Input id="pw2" type="password" value={pw2} onChange={(e) => setPw2(e.target.value)} />
        </div>
        <Button type="submit" variant="energy" size="lg" className="w-full">
          Update password
        </Button>
      </form>
    </AuthShell>
  );
}
