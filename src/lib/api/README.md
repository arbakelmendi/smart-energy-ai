# Frontend API integration (Phase 16)

React 19/TypeScript, TanStack Start SSR/file routes, the existing router QueryClient/root provider, Tailwind and the Lovable Vite wrapper are preserved. Native fetch and existing TanStack Query are used; no dependencies or routes were added.

`VITE_API_BASE_URL` is a public Vite build-time variable. Default: `http://127.0.0.1:8000`. No environment file is required. Supply an HTTP(S) URL, optionally with a path prefix; trailing slashes are removed. Credentials, query strings and fragments are rejected. Never place secrets in VITE variables. A remote browser needs an API URL reachable from that browser; loopback defaults are for local development. Use HTTPS for the API when the frontend is served over HTTPS.

Start the backend from the project root (canonical local model artifact and matching metadata must exist):

```powershell
.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

The existing frontend script is `dev: vite dev`. With the repository Bun workflow, run `bun run dev`. If Bun is unavailable, `npm run dev` executes the same installed Vite script without installing packages or changing package managers/lockfiles. Build: `bun run build` (or `npm run build`). There is no typecheck script; run `node node_modules/typescript/bin/tsc --noEmit`.

Functions: `getHealth`, `getModelInfo`, `getRecommendationThresholds`, `forecast`, `forecastWithRecommendation`. Types mirror `backend/schemas.py`. `ApiError` exposes status (null for connection/timeout failures) and parsed error detail. Server failures have generic UI messages; invalid JSON fails explicitly. Requests time out after 10 seconds unless a caller signal is supplied. GET hooks use TanStack Query cancellation signals. There are no mock fallbacks or automatic POST retries.

Hooks: `useHealth`, `useModelInfo`, `useRecommendationThresholds`, `useForecast`, `useForecastRecommendation`. Queries wait until browser mount, using the existing QueryClient; no SSR API calls, preload or polling is introduced. Queries can refetch on focus/reconnect after their stale period. The existing app-shell header renders real loading/connected/unavailable status, a Retry action and small model metadata. A refresh failure shows unavailable rather than stale success. Other dashboard content remains demo data until the Phase 17 audit/replacement.

The threshold hook/function retrieves the backend's TRAIN + VALIDATION thresholds; the frontend does not classify consumption or hardcode cutoffs. POST functions wrap a supplied feature mapping as `{ features }`. The backend enforces the exact 42-feature schema. Forecasts are Appliances Wh, 10 minutes ahead. The browser cannot construct valid lag_1/6/144/1008 or rolling history from temperature/humidity alone. No raw-sensor form, fabricated histories, development-row production UI, causal control actions or savings estimates are introduced. Recommendations are decision support only.

Default FastAPI CORS origins are `http://localhost:3000`, `http://localhost:5173` and `http://localhost:8080`. Use a matching frontend origin (for example `npm run dev -- --host localhost --port 5173`) or configure the backend's comma-separated `SMARTENERGY_CORS_ORIGINS`. No credentialed cross-origin requests are used.

Focused client tests use the installed Node built-in runner without new packages:

```powershell
node --experimental-strip-types --test tests/frontend_api.test.mjs
```

Tests use clearly identified HTTP fixtures only, never research results. Live POST verification uses a real existing TRAIN row only in the verification process, not in production UI.
