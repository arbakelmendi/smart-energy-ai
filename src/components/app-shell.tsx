import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import {
  Building2,
  ChevronsLeft,
  ChevronsRight,
  Database,
  Gauge,
  LayoutGrid,
  LineChart,
  Lightbulb,
  LogOut,
  Settings,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { BackendStatus } from "@/components/backend-status";
import { Logo } from "@/components/public-layout";
import { useAuth } from "@/lib/auth";
import { Panel } from "@/components/ui-kit";
import { AuthGuard } from "@/components/auth-guard";
import { cn } from "@/lib/utils";

const mainNav = [
  { to: "/dashboard", label: "Dashboard", icon: Gauge },
  { to: "/predictions", label: "Predictions", icon: LineChart },
  { to: "/data", label: "Data & reports", icon: Database },
  { to: "/recommendations", label: "Recommendations", icon: Lightbulb },
  { to: "/buildings", label: "Buildings", icon: Building2 },
] as const;

const adminNav = [
  { to: "/admin", label: "Admin overview", icon: ShieldCheck },
  { to: "/admin/users", label: "Users", icon: Users },
  { to: "/admin/buildings", label: "All buildings", icon: LayoutGrid },
] as const;

export function AppShell(props: { title: string; subtitle?: string; actions?: ReactNode; children: ReactNode }) {
  return <AuthGuard><AuthenticatedShell {...props} /></AuthGuard>;
}

function AuthenticatedShell({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  useEffect(() => setMobileOpen(false), [pathname]);

  const operationalUnavailable = pathname === "/data" || pathname.startsWith("/buildings") || pathname.startsWith("/admin");

  const isAdmin = user?.role === "ADMIN";
  const [logoutError, setLogoutError] = useState("");
  const [loggingOut, setLoggingOut] = useState(false);

  const NavList = () => (
    <>
      <NavGroup label="Operations" collapsed={collapsed}>
        {mainNav.map((n) => (
          <NavItem key={n.to} {...n} collapsed={collapsed} pathname={pathname} />
        ))}
      </NavGroup>
      {isAdmin ? (
        <NavGroup label="Administration" collapsed={collapsed}>
          {adminNav.map((n) => (
            <NavItem key={n.to} {...n} collapsed={collapsed} pathname={pathname} />
          ))}
        </NavGroup>
      ) : null}
      <NavGroup label="Account" collapsed={collapsed}>
        <NavItem
          to="/settings"
          label="Settings"
          icon={Settings}
          collapsed={collapsed}
          pathname={pathname}
        />
      </NavGroup>
    </>
  );

  return (
    <div className="flex min-h-screen bg-background">
      {/* desktop sidebar */}
      <aside
        className={cn(
          "sticky top-0 hidden h-screen shrink-0 flex-col border-r border-sidebar-border bg-sidebar transition-[width] duration-300 lg:flex",
          collapsed ? "w-[74px]" : "w-[258px]",
        )}
      >
        <div className="flex h-16 items-center border-b border-sidebar-border px-4">
          {collapsed ? (
            <Link
              to="/dashboard"
              className="grid size-9 place-items-center rounded-xl border border-efficiency/40 bg-efficiency/10"
            >
              <Gauge className="size-4.5 text-efficiency" />
            </Link>
          ) : (
            <Logo />
          )}
        </div>
        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
          <NavList />
        </nav>
        <div className="border-t border-sidebar-border p-3">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start text-muted-foreground"
            onClick={() => setCollapsed((v) => !v)}
          >
            {collapsed ? <ChevronsRight className="size-4" /> : <ChevronsLeft className="size-4" />}
            {!collapsed && <span>Collapse</span>}
          </Button>
        </div>
      </aside>

      {/* mobile drawer */}
      {mobileOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <div className="relative flex h-full w-[272px] flex-col border-r border-sidebar-border bg-sidebar">
            <div className="flex h-16 items-center justify-between border-b border-sidebar-border px-4">
              <Logo />
              <Button variant="ghost" size="icon" onClick={() => setMobileOpen(false)}>
                <X className="size-4" />
              </Button>
            </div>
            <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
              <NavList />
            </nav>
          </div>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 border-b border-border bg-background/85 backdrop-blur-xl">
          <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-4 py-3 sm:px-6">
            <div className="flex min-w-0 items-center gap-3">
              <Button
                variant="ghost"
                size="icon"
                className="lg:hidden"
                onClick={() => setMobileOpen(true)}
                aria-label="Open navigation"
              >
                <LayoutGrid className="size-4" />
              </Button>
              <div className="min-w-0">
                <h1 className="truncate text-lg font-semibold sm:text-xl">{operationalUnavailable ? "Operational data not connected" : title}</h1>
                {subtitle ? (
                  <p className="truncate text-xs text-muted-foreground">{operationalUnavailable ? "No verified building feed or operational service is available" : subtitle}</p>
                ) : null}
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              <BackendStatus />

              <ThemeToggle />
              <div className="ml-1 hidden items-center gap-2 border-l border-border pl-3 sm:flex">
                <div className="text-right">
                  <p className="max-w-[140px] truncate text-xs font-medium">
                    {user?.full_name}
                  </p>
                  <p className="text-[10px] text-muted-foreground">{user?.role}</p>
                </div>
                <span className="grid size-8 place-items-center rounded-full bg-efficiency/15 font-display text-xs font-bold text-efficiency">
                  {(user?.full_name ?? "")
                    .split(" ")
                    .map((p) => p[0])
                    .slice(0, 2)
                    .join("")}
                </span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Sign out"
                disabled={loggingOut}
                onClick={async () => {
                  setLoggingOut(true); setLogoutError("");
                  try { await signOut(); await navigate({ to: "/login", search: { next: "/dashboard" }, replace: true }); }
                  catch (error) { setLogoutError(error instanceof Error ? error.message : "Unable to sign out."); }
                  finally { setLoggingOut(false); }
                }}
              >
                <LogOut className="size-4" />
              </Button>
            </div>
          </div>
          {actions && !operationalUnavailable ? (
            <div className="flex flex-wrap items-center gap-2 border-t border-border/60 px-4 py-2.5 sm:px-6">
              {actions}
            </div>
          ) : null}
        </header>
        <main key={pathname} className="rise-in min-w-0 flex-1 px-4 py-6 sm:px-6 lg:py-8">
          {logoutError ? <p role="alert" className="mb-4 text-sm text-destructive">{logoutError}</p> : null}
          {operationalUnavailable ? <Panel title="Not connected" subtitle="Operational capability unavailable">
            <p className="text-sm text-muted-foreground">No verified operational readings, building records or management service is connected. This prototype does not provide live measurements or equipment control.</p>
            <Link to="/dashboard" className="mt-4 inline-block text-sm text-efficiency underline">View verified research results</Link>
          </Panel> : children}
        </main>
      </div>
    </div>
  );
}

function NavGroup({
  label,
  collapsed,
  children,
}: {
  label: string;
  collapsed: boolean;
  children: ReactNode;
}) {
  return (
    <div>
      {!collapsed ? (
        <p className="mb-2 px-3 font-mono text-[10px] tracking-[0.18em] text-muted-foreground uppercase">
          {label}
        </p>
      ) : null}
      <ul className="space-y-1">{children}</ul>
    </div>
  );
}

function NavItem({
  to,
  label,
  icon: Icon,
  collapsed,
  pathname,
}: {
  to: string;
  label: string;
  icon: typeof Gauge;
  collapsed: boolean;
  pathname: string;
}) {
  const active = to === "/admin" ? pathname === "/admin" : pathname.startsWith(to);
  return (
    <li>
      <Link
        to={to}
        title={label}
        className={cn(
          "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors",
          active
            ? "bg-efficiency/12 font-medium text-efficiency"
            : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        )}
      >
        {active ? (
          <span className="absolute top-1/2 left-0 h-6 w-[3px] -translate-y-1/2 rounded-r-full bg-efficiency" />
        ) : null}
        <Icon className="size-4.5 shrink-0" strokeWidth={active ? 2.4 : 1.9} />
        {!collapsed && <span className="truncate">{label}</span>}
      </Link>
    </li>
  );
}
