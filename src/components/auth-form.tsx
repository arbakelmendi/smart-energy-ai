import { Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";
import { AuthShell } from "@/components/auth-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth";
import { safeDestination } from "@/lib/auth-policy";

export function AuthenticationForm({ mode, next }: { mode: "login" | "signup"; next?: string | undefined }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const signup = mode === "signup";
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const email = String(values.get("email") ?? "");
    const password = String(values.get("password") ?? "");
    setError("");
    if (signup && password !== values.get("confirm_password")) { setError("Passwords do not match."); return; }
    if (signup && !String(values.get("full_name") ?? "").trim()) { setError("Enter your full name."); return; }
    setPending(true);
    try {
      if (signup) await auth.signUp({ full_name: String(values.get("full_name")), email, password });
      else await auth.signIn({ email, password });
      form.reset();
      await navigate({ to: safeDestination(next), replace: true });
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to complete authentication.");
    } finally { setPending(false); }
  }
  return <AuthShell title={signup ? "Create an account" : "Sign in"}
    subtitle={signup ? "Create a USER account. Email verification is not provided." : "Use your account to open the research dashboard."}
    footer={signup ? <Link to="/login">Already registered? Sign in</Link> : <Link to="/signup">Create an account</Link>}>
    <form method="post" onSubmit={submit}><fieldset disabled={!hydrated || pending} className="min-w-0 space-y-4">
      {signup ? <label className="block text-sm">Full name<Input name="full_name" autoComplete="name" required maxLength={200} className="mt-2" /></label> : null}
      <label className="block text-sm">Email<Input name="email" type="email" autoComplete="email" required maxLength={320} className="mt-2" /></label>
      <label className="block text-sm">Password<Input name="password" type="password" autoComplete={signup ? "new-password" : "current-password"} required minLength={signup ? 12 : 1} maxLength={128} className="mt-2" /></label>
      {signup ? <><p className="text-xs text-muted-foreground">Use 12-128 characters.</p><label className="block text-sm">Confirm password<Input name="confirm_password" type="password" autoComplete="new-password" required minLength={12} maxLength={128} className="mt-2" /></label></> : null}
      {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
      <Button type="submit" variant="energy" disabled={pending} className="w-full">{pending ? "Please wait..." : signup ? "Create account" : "Sign in"}</Button>
      {!signup ? <p className="text-xs text-muted-foreground">Invalid credentials and inactive accounts receive the same safe login error. <Link to="/forgot-password" className="underline">Password reset status</Link></p> : null}
    </fieldset></form>
  </AuthShell>;
}
