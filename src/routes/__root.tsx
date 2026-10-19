import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";
import { Activity } from "lucide-react";

import appCss from "../styles.css?url";
import { reportLovableError } from "../lib/lovable-error-reporting";
import { ThemeProvider } from "../lib/theme";
import { AuthProvider } from "../lib/auth";
import { Toaster } from "../components/ui/sonner";

function NotFoundComponent() {
  return (
    <div className="mesh-bg relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <div className="grid-lines absolute inset-0 -z-10" />
      <div className="panel relative max-w-lg p-10 text-center">
        <span className="mx-auto grid size-12 place-items-center rounded-2xl border border-peak/40 bg-peak/10">
          <Activity className="size-6 text-peak" />
        </span>
        <p className="stat-number mt-6 text-6xl font-bold text-peak">404</p>
        <h1 className="mt-3 text-xl font-semibold">Signal lost — page not found</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          This route isn't wired to any sensor. The telemetry stream you're looking for may have
          moved or was never deployed.
        </p>
        <div className="mt-7 flex flex-wrap justify-center gap-2">
          <Link
            to="/"
            className="inline-flex h-9 items-center rounded-lg bg-efficiency px-4 text-sm font-semibold text-efficiency-foreground glow-ring"
          >
            Back to landing
          </Link>
          <Link
            to="/dashboard"
            className="inline-flex h-9 items-center rounded-lg border border-border px-4 text-sm hover:bg-muted"
          >
            Open dashboard
          </Link>
        </div>
        <p className="mt-6 font-mono text-[11px] tracking-wider text-muted-foreground uppercase">
          error_code: route_unmapped · smart-energy-ai
        </p>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportLovableError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="panel max-w-md p-8 text-center">
        <h1 className="text-xl font-semibold tracking-tight">This page didn't load</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Something went wrong while rendering the telemetry. Try again or head back home.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="inline-flex h-9 items-center rounded-lg bg-efficiency px-4 text-sm font-semibold text-efficiency-foreground"
          >
            Try again
          </button>
          <a
            href="/"
            className="inline-flex h-9 items-center rounded-lg border border-border px-4 text-sm hover:bg-muted"
          >
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "Smart Energy AI — ML forecasting for smart buildings" },
      {
        name: "description",
        content:
          "Verified energy forecasting research and forecast-based decision support. No live operational feed or automatic equipment control.",
      },
      { name: "author", content: "Smart Energy AI — UBT thesis project" },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "icon", href: "/favicon.ico", type: "image/x-icon" },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap",
      },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark" style={{ colorScheme: "dark" }}>
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          {/* Required: nested routes render here. Removing <Outlet /> breaks all child routes. */}
          <Outlet />
          <Toaster />
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
