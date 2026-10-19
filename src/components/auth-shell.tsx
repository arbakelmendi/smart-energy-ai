import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { EnergyWave } from "@/components/energy-wave";
import { Logo } from "@/components/public-layout";
import { ThemeToggle } from "@/components/theme-toggle";

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
  aside,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer?: ReactNode;
  aside?: ReactNode;
}) {
  return (
    <div className="mesh-bg relative flex min-h-screen flex-col overflow-hidden">
      <div className="grid-lines absolute inset-0 -z-10" />
      <EnergyWave className="absolute inset-x-0 top-1/3 -z-10 h-56 opacity-40" />
      <header className="flex items-center justify-between px-4 py-4 sm:px-6">
        <Logo />
        <ThemeToggle />
      </header>
      <div className="mx-auto grid w-full max-w-6xl flex-1 items-center gap-12 px-4 py-8 sm:px-6 lg:grid-cols-[1fr_minmax(0,440px)]">
        <div className="hidden min-w-0 lg:block">
          <p className="font-mono text-[11px] tracking-[0.2em] text-efficiency uppercase">
            smart energy ai | research prototype
          </p>
          <h2 className="mt-4 text-4xl leading-tight font-bold">
            Inspect verified energy forecasting results.
          </h2>
          <p className="mt-4 max-w-md text-sm text-muted-foreground">
            The research dashboard shows verified model performance and decision-support thresholds. No account or live building connection is required.
          </p>
          {aside}
        </div>
        <div className="panel glow-ring w-full p-7 sm:p-8">
          <h1 className="text-2xl font-semibold">{title}</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">{subtitle}</p>
          <div className="mt-7">{children}</div>
          {footer ? <div className="mt-6 text-sm text-muted-foreground">{footer}</div> : null}
        </div>
      </div>
      <footer className="px-4 py-5 text-center text-xs text-muted-foreground sm:px-6">
        <Link to="/" className="hover:text-efficiency">
          ← Back to the prototype
        </Link>
      </footer>
    </div>
  );
}
