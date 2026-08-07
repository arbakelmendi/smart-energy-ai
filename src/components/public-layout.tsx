import { Link } from "@tanstack/react-router";
import { Activity, Github, Mail, MapPin, Menu } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/", label: "Home" },
  { to: "/about", label: "About the project" },
  { to: "/contact", label: "Contact" },
];

export function Logo({ className }: { className?: string }) {
  return (
    <Link to="/" className={cn("flex items-center gap-2.5", className)}>
      <span className="relative grid size-9 shrink-0 place-items-center rounded-xl border border-efficiency/40 bg-efficiency/10">
        <Activity className="size-4.5 text-efficiency" strokeWidth={2.4} />
        <span className="absolute -top-0.5 -right-0.5 size-1.5 rounded-full bg-efficiency pulse-dot" />
      </span>
      <span className="min-w-0 leading-tight">
        <span className="block font-display text-sm font-bold tracking-tight">Smart Energy AI</span>
        <span className="block font-mono text-[10px] tracking-[0.16em] text-muted-foreground uppercase">
          forecast · optimize
        </span>
      </span>
    </Link>
  );
}

export function PublicHeader() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto grid max-w-7xl grid-cols-[minmax(0,1fr)_auto] items-center gap-4 px-4 py-3 sm:px-6">
        <Logo />
        <div className="flex items-center gap-1">
          <nav className="mr-2 hidden items-center gap-1 md:flex">
            {nav.map((n) => (
              <Link
                key={n.to}
                to={n.to}
                activeOptions={{ exact: n.to === "/" }}
                className="rounded-lg px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground data-[status=active]:text-efficiency"
              >
                {n.label}
              </Link>
            ))}
          </nav>
          <ThemeToggle />
          <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
            <Link to="/login">Log in</Link>
          </Button>
          <Button asChild size="sm" variant="energy">
            <Link to="/signup">Request demo</Link>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            aria-label="Open menu"
            onClick={() => setOpen((v) => !v)}
          >
            <Menu className="size-4" />
          </Button>
        </div>
      </div>
      {open ? (
        <nav className="border-t border-border bg-surface px-4 py-2 md:hidden">
          {[...nav, { to: "/login", label: "Log in" }].map((n) => (
            <Link
              key={n.to}
              to={n.to}
              onClick={() => setOpen(false)}
              className="block rounded-lg px-3 py-2.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              {n.label}
            </Link>
          ))}
        </nav>
      ) : null}
    </header>
  );
}

export function PublicFooter() {
  return (
    <footer className="border-t border-border bg-surface/50">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div className="space-y-4">
          <Logo />
          <p className="max-w-xs text-sm text-muted-foreground">
            Machine-learning forecasting and optimization of energy consumption in smart buildings.
            Built as a bachelor thesis project at UBT — University for Business and Technology.
          </p>
          <p className="font-mono text-[11px] text-muted-foreground">
            Active model: LSTM seq-48 v4.2 · MAE 12.4 kWh · R² 0.962
          </p>
        </div>
        <FooterCol
          title="Platform"
          links={[
            { to: "/dashboard", label: "Dashboard" },
            { to: "/predictions", label: "Predictions" },
            { to: "/data", label: "Data & reports" },
            { to: "/recommendations", label: "Recommendations" },
          ]}
        />
        <FooterCol
          title="Project"
          links={[
            { to: "/about", label: "About the project" },
            { to: "/contact", label: "Contact & support" },
            { to: "/signup", label: "Create account" },
            { to: "/login", label: "Log in" },
          ]}
        />
        <div className="space-y-3 text-sm text-muted-foreground">
          <p className="font-display text-xs font-semibold tracking-wide text-foreground uppercase">
            Contact
          </p>
          <p className="flex items-start gap-2">
            <MapPin className="mt-0.5 size-4 shrink-0 text-efficiency" />
            UBT Innovation Campus, Lipjan, Kosovo
          </p>
          <p className="flex items-start gap-2">
            <Mail className="mt-0.5 size-4 shrink-0 text-efficiency" />
            research@smart-energy-ai.dev
          </p>
          <p className="flex items-start gap-2">
            <Github className="mt-0.5 size-4 shrink-0 text-efficiency" />
            github.com/smart-energy-ai
          </p>
        </div>
      </div>
      <div className="border-t border-border px-4 py-5 text-center text-xs text-muted-foreground sm:px-6">
        © 2026 Smart Energy AI · Academic research prototype · All consumption data shown is
        simulated.
      </div>
    </footer>
  );
}

function FooterCol({ title, links }: { title: string; links: Array<{ to: string; label: string }> }) {
  return (
    <div>
      <p className="font-display text-xs font-semibold tracking-wide uppercase">{title}</p>
      <ul className="mt-3 space-y-2">
        {links.map((l) => (
          <li key={l.to}>
            <Link
              to={l.to}
              className="text-sm text-muted-foreground transition-colors hover:text-efficiency"
            >
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <PublicHeader />
      <main className="flex-1">{children}</main>
      <PublicFooter />
    </div>
  );
}
