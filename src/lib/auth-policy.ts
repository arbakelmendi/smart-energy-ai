import type { AuthUser } from "./api/auth.ts";

export const isAdminPath = (path: string) => /^\/admin(?:\/|$)/.test(path);
export const isProtectedPath = (path: string) => /^\/(dashboard|predictions|recommendations|data|settings|buildings(?:\/[^?#]*)?|admin(?:\/[^?#]*)?)$/.test(path);
export function safeDestination(value: unknown): string {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) return "/dashboard";
  const url = new URL(value, "http://local.invalid");
  return url.origin === "http://local.invalid" && isProtectedPath(url.pathname)
    ? url.pathname : "/dashboard";
}
export function accessDecision(ready: boolean, error: boolean, user: AuthUser | null, path: string) {
  if (!ready) return "checking";
  if (error) return "unavailable";
  if (!user) return "login";
  if (isAdminPath(path) && user.role !== "ADMIN") return "forbidden";
  return "allowed";
}
