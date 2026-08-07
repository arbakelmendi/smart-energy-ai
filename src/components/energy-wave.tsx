/** Decorative animated energy-wave background (pure SVG, no deps). */
export function EnergyWave({ className = "" }: { className?: string }) {
  const path =
    "M0 120 C 60 60, 120 180, 180 120 S 300 60, 360 120 S 480 180, 540 120 S 660 60, 720 120";
  return (
    <div className={`pointer-events-none overflow-hidden ${className}`} aria-hidden="true">
      <svg viewBox="0 0 720 240" className="h-full w-[200%] wave-scroll" preserveAspectRatio="none">
        <defs>
          <linearGradient id="wave-a" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="var(--efficiency)" stopOpacity="0" />
            <stop offset="45%" stopColor="var(--efficiency)" stopOpacity="0.9" />
            <stop offset="100%" stopColor="var(--info)" stopOpacity="0.1" />
          </linearGradient>
          <linearGradient id="wave-b" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="var(--peak)" stopOpacity="0" />
            <stop offset="60%" stopColor="var(--peak)" stopOpacity="0.55" />
            <stop offset="100%" stopColor="var(--peak)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={path} fill="none" stroke="url(#wave-a)" strokeWidth="2" />
        <path
          d={path}
          fill="none"
          stroke="url(#wave-b)"
          strokeWidth="1.5"
          transform="translate(0 34) scale(1 0.8)"
        />
        <path
          d={path}
          fill="none"
          stroke="url(#wave-a)"
          strokeWidth="1"
          strokeOpacity="0.5"
          transform="translate(0 70) scale(1 0.6)"
        />
      </svg>
    </div>
  );
}

/** Small inline sparkline used inside cards. */
export function Sparkline({
  points,
  tone = "efficiency",
  className = "",
}: {
  points: number[];
  tone?: "efficiency" | "peak" | "info";
  className?: string;
}) {
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const d = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * 100;
      const y = 30 - ((p - min) / span) * 26 - 2;
      return `${i === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
  const id = `spark-${tone}-${points.length}`;
  return (
    <svg viewBox="0 0 100 30" className={className} preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={`var(--${tone})`} stopOpacity="0.35" />
          <stop offset="100%" stopColor={`var(--${tone})`} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${d} L100 30 L0 30 Z`} fill={`url(#${id})`} />
      <path d={d} fill="none" stroke={`var(--${tone})`} strokeWidth="1.6" />
    </svg>
  );
}
