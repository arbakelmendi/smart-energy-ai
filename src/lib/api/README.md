# Frontend API integration

React 19/TypeScript, TanStack Start SSR/file routes, the existing router QueryClient/root provider, Tailwind and the Lovable Vite wrapper are preserved. Native fetch and existing TanStack Query are used; no dependencies or routes were added.

`VITE_API_BASE_URL` is a public Vite build-time variable. Default: `http://localhost:8000`. No environment file is required. Supply an HTTP(S) URL, optionally with a path prefix; trailing slashes are removed. Credentials, query strings and fragments are rejected. Never place secrets in VITE variables. A remote browser needs an API URL reachable from that browser; loopback defaults are for local development. Use HTTPS for the API when the frontend is served over HTTPS.

Start the backend from the project root (canonical local model artifact and matching metadata must exist):

```powershell
.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

The existing scripts are `dev: vite dev` and `build: vite build`. Verified local commands are `npm run dev -- --host localhost --port 5173 --strictPort` and `npm run build`, using installed dependencies. Bun was unavailable in recorded QA; no Bun command is claimed as verified. Preserve the existing Bun/npm state and lockfiles. There is no typecheck script; run `node node_modules/typescript/bin/tsc --noEmit`.

Functions: `getHealth`, `getModelInfo`, `getRecommendationThresholds`, `forecast`, `forecastWithRecommendation`. Types mirror `backend/schemas.py`. `ApiError` exposes status (null for connection/timeout failures) and parsed error detail. Server failures have generic UI messages; invalid JSON fails explicitly. Requests time out after 10 seconds unless a caller signal is supplied. GET hooks use TanStack Query cancellation signals. There are no mock fallbacks or automatic POST retries.

Hooks: `useHealth`, `useModelInfo`, `useRecommendationThresholds`, `useForecast`, `useForecastRecommendation`. Queries wait until browser mount, using the existing QueryClient; no SSR API calls, preload or polling is introduced. Queries can refetch on focus/reconnect after their stale period. The existing app-shell header renders real loading/connected/unavailable status, a Retry action and small model metadata. A refresh failure shows unavailable rather than stale success. Dashboard research panels now use verified API results; unsupported operational views are explicitly unavailable.

The threshold hook/function retrieves the backend's TRAIN + VALIDATION thresholds; the frontend does not classify consumption or hardcode cutoffs. POST functions wrap a supplied feature mapping as `{ features }`. The backend enforces the exact 42-feature schema. Forecasts are Appliances Wh, 10 minutes ahead. The browser cannot construct valid lag_1/6/144/1008 or rolling history from temperature/humidity alone. No raw-sensor form, fabricated histories, development-row production UI, causal control actions or savings estimates are introduced. Recommendations are decision support only.

Default FastAPI CORS origins are `http://localhost:3000`, `http://localhost:5173` and `http://localhost:8080`. Use a matching frontend origin (for example `npm run dev -- --host localhost --port 5173`) or configure the backend's comma-separated `SMARTENERGY_CORS_ORIGINS`. Auth functions use credentialed requests and X-SmartEnergy-CSRF; public research calls still omit credentials. FastAPI allows credentials with explicit origins. Use localhost consistently for cookie SameSite behavior.

Focused client tests use the installed Node built-in runner without new packages:

```powershell
node --experimental-strip-types --test tests/frontend_api.test.mjs
```

Tests use clearly identified HTTP fixtures only, never research results. Live POST verification uses a real existing TRAIN row only in the verification process, not in production UI.


## Phase 17 dashboard presentation

Dashboard, predictions and recommendations now share verified research panels. The existing API client adds `getModelComparison` and `getFeatureImportance`, with `useModelComparison` and `useFeatureImportance`. Research response shapes are checked with the already-installed Zod library; malformed data produces an explicit error with Retry. Existing forecast mutations remain available but are not called to populate the dashboard.

Model KPIs come from `/model/info` and are labeled held-out test; six-model comparison comes from `/analysis/model-comparison` and is validation-only. Top-ten normalized gain comes from `/analysis/feature-importance`, labeled predictive rather than causal. Recommendation bands display definitions and values from `/recommendations/thresholds`; the browser does not classify forecasts. No live forecast, recommendations, histories, savings or uncertainty intervals are fabricated.

The app shell disables unsupported data/building/admin operational views and hides their action buttons. Their legacy implementation files are preserved; they are not displayed as working services. Phase 18 corrected legacy public/account claims; account, email and building-setup services are explicitly unavailable. No new routes or providers are added.


Optional repeatable Windows browser regression: `.venv\Scripts\python.exe tests/verify_dashboard_browser.py`. Uses the installed Edge browser and `websocket-client` already present in the project's Jupyter environment, not a new browser test framework. Requires free ports 8000/5173 and installed frontend dependencies. It starts/stops only its verification processes, blocks external page requests, verifies desktop/mobile/error states, and saves ignored screenshots/evidence under `ml/results/generated`. `SMARTENERGY_BROWSER` can override the Edge executable. Phase 18 includes a route-wide browser QA mode: append `--phase18` to this command. Public/account pages no longer claim working account services.

Phase 18 repeatable automated gates: `.venv\Scripts\python.exe tests/verify_phase18.py`; add `--browser` for the full local Edge/API/route checks. The script records targeted formatting findings separately from semantic lint and does not reformat unrelated files.

Current architecture and complete setup/reproduction prerequisites are in the [architecture guide](../../../docs/system-architecture.md) and [reproducibility guide](../../../docs/reproducibility.md). The current endpoint/client additions are read-only analysis results, not a new live forecasting feed.

Phase 22 adds typed `auth.ts` functions (`signup`, `login`, `logout`, `getCurrentUser`) over the same transport and ApiError. Account responses are validated without fallback; server state supplies USER/ADMIN roles. See [authentication](../../../docs/authentication.md).
