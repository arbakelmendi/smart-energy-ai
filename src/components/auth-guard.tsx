import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import { accessDecision, isProtectedPath } from "@/lib/auth-policy";
import { Button } from "@/components/ui/button";

export function AuthGuard({ children }: { children: ReactNode }) {
  const { user, ready, error, retry } = useAuth();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const decision = accessDecision(ready, !!error, user, pathname);
  useEffect(() => {
    if (decision === "login" && isProtectedPath(pathname)) void navigate({ to: "/login", search: { next: pathname }, replace: true });
  }, [decision, navigate, pathname]);
  if (decision === "allowed") return children;
  return <main className="mx-auto max-w-xl px-6 py-16">
    <h1 className="text-2xl font-semibold">{decision === "forbidden" ? "Administrator access required" : decision === "unavailable" ? "Unable to verify session" : "Checking session"}</h1>
    {decision === "forbidden" ? <p className="mt-4">Your account cannot access administration. <Link to="/dashboard" className="text-efficiency underline">Return to dashboard</Link></p> : null}
    {decision === "unavailable" ? <div role="alert" className="mt-4 space-y-4"><p>Check the backend connection, then retry. No authenticated content is shown while verification is unavailable.</p><Button onClick={retry}>Retry session</Button><Link to="/login" className="ml-4 underline">Sign in</Link></div> : null}
  </main>;
}
