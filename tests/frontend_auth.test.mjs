// Runtime-only fixtures test transport/guards, never operational credentials.
import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { randomBytes } from "node:crypto";
import { readFileSync } from "node:fs";
import { ApiError } from "../src/lib/api/client.ts";
import { signup, login, logout, getCurrentUser } from "../src/lib/api/auth.ts";
import { accessDecision, safeDestination, isAdminPath, isProtectedPath } from "../src/lib/auth-policy.ts";

const user = { id: 1, email: "fixture@example.com", full_name: "Transport fixture", role: "USER", is_active: true };
const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });
function respond(payload, status = 200) {
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return new Response(JSON.stringify(payload), { status, headers: { "Content-Type": "application/json" } });
  };
  return calls;
}

test("signup sends payload and credentialed CSRF request", async () => {
  const body = { email: user.email, full_name: user.full_name, password: randomBytes(20).toString("hex") };
  const calls = respond(user, 201);
  assert.deepEqual(await signup(body), user);
  assert.equal(calls[0].options.credentials, "include");
  assert.equal(calls[0].options.headers["X-SmartEnergy-CSRF"], "1");
  assert.deepEqual(JSON.parse(calls[0].options.body), body);
  assert.ok(calls[0].url.endsWith("/auth/signup"));
});
test("login sends only supplied credentials and includes cookies", async () => {
  const body = { email: user.email, password: randomBytes(20).toString("hex") };
  const calls = respond(user);
  await login(body);
  assert.deepEqual(JSON.parse(calls[0].options.body), body);
  assert.equal(calls[0].options.credentials, "include");
  assert.equal(calls[0].options.method, "POST");
});
test("logout is real POST with credentialed CSRF header", async () => {
  const calls = respond({ detail: "Signed out" });
  await logout();
  assert.ok(calls[0].url.endsWith("/auth/logout"));
  assert.equal(calls[0].options.method, "POST");
  assert.equal(calls[0].options.credentials, "include");
  assert.equal(calls[0].options.headers["X-SmartEnergy-CSRF"], "1");
});
test("current-user uses cookies and never invents a profile", async () => {
  const calls = respond(user);
  assert.deepEqual(await getCurrentUser(), user);
  assert.equal(calls[0].options.credentials, "include");
  assert.ok(calls[0].url.endsWith("/auth/me"));
});
test("401/inactive login and duplicate errors preserve ApiError", async () => {
  for (const [fn, status] of [[getCurrentUser,401], [() => login({ email:user.email,password:randomBytes(20).toString("hex") }),401], [() => signup({email:user.email,password:randomBytes(20).toString("hex"),full_name:user.full_name}),409]]) {
    respond({ detail: "Safe test error" }, status);
    await assert.rejects(fn(), e => e instanceof ApiError && e.status === status && e.message === "Safe test error");
  }
});
test("malformed or inactive accounts and extra secrets fail closed", async () => {
  for (const value of [{}, {...user,role:"Platform Admin"}, {...user,is_active:false}, {...user,token:"must-not-exist"}, {...user,password_hash:"must-not-exist"}]) {
    respond(value);
    await assert.rejects(getCurrentUser(), e => e instanceof ApiError && /malformed account/.test(e.message));
  }
});
test("network failure has no successful auth fallback", async () => {
  globalThis.fetch = async () => { throw new TypeError("offline"); };
  await assert.rejects(getCurrentUser(), e => e instanceof ApiError && e.status === null);
});
test("guard holds SSR/loading and unavailable state before content", () => {
  assert.equal(accessDecision(false,false,user,"/dashboard"),"checking");
  assert.equal(accessDecision(true,true,user,"/dashboard"),"unavailable");
  assert.equal(accessDecision(true,false,null,"/dashboard"),"login");
  assert.equal(accessDecision(true,false,user,"/dashboard"),"allowed");
});
test("USER forbidden from every admin route; ADMIN allowed", () => {
  for (const path of ["/admin","/admin/","/admin/users","/admin/buildings"]) {
    assert.equal(isAdminPath(path),true);
    assert.equal(accessDecision(true,false,user,path),"forbidden");
    assert.equal(accessDecision(true,false,{...user,role:"ADMIN"},path),"allowed");
  }
  assert.equal(isAdminPath("/administrator"),false);
});
test("intended destination cannot redirect externally or back to auth", () => {
  for (const path of ["https://untrusted.example", "//untrusted.example", "/\\untrusted.example", "/login", "/signup", "javascript:alert(1)", null]) assert.equal(safeDestination(path),"/dashboard");
  assert.equal(safeDestination("/settings"),"/settings");
  assert.equal(safeDestination("/admin/users"),"/admin/users");
});
test("auth provider has no localStorage identity and shell uses USER/ADMIN role", () => {
  const provider=readFileSync(new URL("../src/lib/auth.tsx",import.meta.url),"utf8");
  for (const forbidden of ["parseDemoSession", "localStorage.getItem", "localStorage.setItem", "const DEMO", "new QueryClient"]) assert.ok(!provider.includes(forbidden));
  assert.ok(provider.includes("getCurrentUser"));
  const shell=readFileSync(new URL("../src/components/app-shell.tsx",import.meta.url),"utf8");
  assert.ok(shell.includes('user?.role === "ADMIN"'));
  assert.ok(shell.includes("<AuthGuard>"));
  assert.ok(!shell.includes("Demo User"));
});

test("auth forms cannot fall through to URL credentials before hydration", () => {
  const source=readFileSync(new URL("../src/components/auth-form.tsx",import.meta.url),"utf8");
  assert.ok(source.includes('method="post"'));
  assert.ok(source.includes('disabled={!hydrated || pending}'));
  assert.ok(source.includes('useState(false)'));
});

test("guard does not overwrite intended destination during transition to a public route", () => {
  assert.equal(isProtectedPath("/settings"),true);
  assert.equal(isProtectedPath("/login"),false);
  assert.equal(isProtectedPath("/signup"),false);
  assert.equal(isProtectedPath("/"),false);
  const source=readFileSync(new URL("../src/components/auth-guard.tsx",import.meta.url),"utf8");
  assert.ok(source.includes('decision === "login" && isProtectedPath(pathname)'));
});
