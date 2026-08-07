import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { CountUp } from "@/components/count-up";
import { Sparkline } from "@/components/energy-wave";

export function StatCard({
  label,
  value,
  unit,
  decimals = 0,
  delta,
  tone = "efficiency",
  icon,
  spark,
  className,
}: {
  label: string;
  value: number;
  unit?: string;
  decimals?: number;
  delta?: string;
  tone?: "efficiency" | "peak" | "info";
  icon?: ReactNode;
  spark?: number[];
  className?: string;
}) {
  return (
    <div className={cn("panel lift relative overflow-hidden p-5", className)}>
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{label}</p>
        {icon ? <span className={cn("shrink-0", `text-${tone}`)}>{icon}</span> : null}
      </div>
      <p className="stat-number mt-3 text-3xl font-semibold">
        <CountUp value={value} decimals={decimals} />
        {unit ? <span className="ml-1 text-base font-normal text-muted-foreground">{unit}</span> : null}
      </p>
      {delta ? (
        <p className={cn("mt-1 text-xs", tone === "peak" ? "text-peak" : "text-efficiency")}>{delta}</p>
      ) : null}
      {spark ? (
        <Sparkline points={spark} tone={tone} className="mt-4 h-10 w-full" />
      ) : null}
    </div>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  action,
  className,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "grid grid-cols-[minmax(0,1fr)_auto] items-end gap-4 sm:flex sm:flex-wrap sm:justify-between",
        className,
      )}
    >
      <div className="min-w-0">
        {eyebrow ? (
          <p className="mb-1.5 font-mono text-[11px] tracking-[0.2em] text-efficiency uppercase">
            {eyebrow}
          </p>
        ) : null}
        <h2 className="text-2xl font-semibold sm:text-3xl">{title}</h2>
        {description ? (
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {action}
    </div>
  );
}

export function Panel({
  title,
  subtitle,
  action,
  children,
  className,
  bodyClassName,
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cn("panel overflow-hidden", className)}>
      {(title || action) && (
        <header className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-b border-border px-5 py-4 sm:flex sm:justify-between">
          <div className="min-w-0">
            {title ? <h3 className="truncate text-base font-semibold">{title}</h3> : null}
            {subtitle ? <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p> : null}
          </div>
          {action}
        </header>
      )}
      <div className={cn("p-5", bodyClassName)}>{children}</div>
    </section>
  );
}

export function MetricPill({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface-2/60 px-4 py-3">
      <p className="font-mono text-[10px] tracking-[0.18em] text-muted-foreground uppercase">
        {label}
      </p>
      <p className="stat-number mt-1 text-xl font-semibold">{value}</p>
      {hint ? <p className="mt-0.5 text-[11px] text-muted-foreground">{hint}</p> : null}
    </div>
  );
}
