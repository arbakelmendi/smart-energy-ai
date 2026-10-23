# Administrator management (Phase 28)

## Setup and role boundary

Follow [reproducibility](reproducibility.md) and [authentication](authentication.md). Upgrade the existing database with `python -m alembic upgrade head`, provision an administrator with `python scripts/create_admin.py` when needed, start the existing API/frontend, and log in using localhost consistently. Phase28 adds no dependency, schema migration, background process or authentication mechanism.

Every dedicated `/admin/...` API requires the existing `require_admin` dependency. Missing/expired/inactive authentication returns401; authenticated USER returns403. The existing frontend role guard prevents rendering admin pages and the sidebar shows Administration only for ADMIN. The backend remains authoritative. Admin responses use `Cache-Control: no-store`; PATCH also requires existing CSRF and trusted-origin checks.

Ordinary `/buildings` and its detail, measurement, readiness, dashboard and forecast routes remain owner-only, including for ADMIN. Cross-owner access exists only under `/admin`. Administration does not change the UCI reference building's owner or expose it to ordinary users.

## Endpoints

| Method | Path | Contents |
| --- | --- | --- |
| GET | `/admin/overview` | Eight factual database counts |
| GET | `/admin/users` | Paginated safe users and building counts |
| GET | `/admin/users/{user_id}` | Safe account and owned building/measurement/prediction counts |
| PATCH | `/admin/users/{user_id}/status` | Strict `{ "is_active": false }` or true; confirmed updated detail |
| GET | `/admin/buildings` | Paginated cross-owner inventory, safe owners and aggregate counts |
| GET | `/admin/buildings/{building_id}` | Metadata, owner, measurement range and latest saved prediction summary |
| GET | `/admin/predictions` | Paginated newest-saved-first forecast activity with building/owner context |

Lists default to limit50/offset0, with limit1-200 and nonnegative signed64-bit offset. Users/buildings use stable ID ascending order. Predictions use created_at descending then ID descending. Offset pagination is a current database view, not a historical transaction snapshot; concurrent insertions can move pages.

Users support `search` (email/full_name substring), `role=USER|ADMIN` and `is_active=true|false`. Buildings support `search` (name/city substring), positive `owner_id` and exact `building_type`. Search trims/collapses whitespace, is case-insensitive under the database's comparison semantics and escapes literal SQL percent/underscore characters. SQLite's default Unicode case-folding limits apply. Filtering and pagination execute server-side. No full-text infrastructure is added.

## Counts and activity semantics

Overview reports total_users, active_users, inactive_users, admin_users, regular_users, total_buildings, total_measurements and total_predictions. Role counts include inactive accounts; active/inactive are separate counts. All values come from SQL, including genuine zero counts. There are no growth percentages, savings, accuracy scores, online-building/sensor counts or fabricated login events.

Dedicated services use SQL aggregates and bounded page queries rather than loading raw histories or issuing one child-count query per displayed row. User detail's owned buildings are separately paginated using the owner filter. Building detail returns earliest/latest measurement timestamps and the latest prediction by saved creation time, explicitly **not necessarily current**. Admin pages do not assess full-building ML readiness, invoke inference or reconstruct features. Prediction activity describes persisted forecasts in Wh, not measured consumption or a complete security audit log.

Measurement and forecast source/target timestamps retain the existing naive building-local policy. Account/building creation/update timestamps and prediction saved timestamps are labeled UTC. Read-only administration does not establish external model validation. Reference metadata/descriptions are shown as stored; other-building forecasts remain experimental.

## Activation, deactivation and lockout prevention

From Users, open an account detail to activate or deactivate it. Deactivation requires an explicit confirmation explaining that login will be prevented and active sessions invalidated. Cancel sends no status request. The UI does not optimistically change status; it waits for the server, then invalidates that administrator's user lists/details and overview counts. Activation permits a new login.

The backend updates status and deletes **all** target AuthSession rows in one transaction when deactivating, including repeated deactivation requests. Existing tokens fail their next authenticated request immediately rather than remaining valid until cookie expiration. Buildings, measurements and predictions remain stored. Reactivation does not recreate revoked sessions. Authentication still uses the original active-account check on every request.

An administrator cannot deactivate their own authenticated account. The final active ADMIN cannot be deactivated. Both return safe409 messages. Active-admin row locking where supported, plus an atomic conditional status UPDATE, protects the final-admin invariant; the isolated SQLite test includes simultaneous mutually targeted deactivation. Live PostgreSQL concurrency has not been verified. As with the existing session system, a request already authorized before a concurrent deactivation can finish; subsequent authentication fails.

The existing frontend auth revalidation on navigation/focus/its60-second interval and401 query handling protects an open client after revocation. There is no server push channel: backend access is revoked immediately, while an idle already-rendered client learns on its next revalidation/request. The browser verifier checks the revoked cookie and frontend redirect explicitly.

Role editing is deliberately omitted. Use the existing explicit administrator CLI for provisioning; public signup cannot choose a role. User deletion, password visibility/reset, email, MFA and cross-owner building/history mutation are unsupported. Retained account/domain data avoids destructive administration cascades.

## Frontend routes and cache isolation

Existing routes are reused without a generated route-tree edit:

- `/admin`: database overview and paginated prediction activity.
- `/admin/users`: filtered account list; `?user=123` opens safe detail, status actions and a paginated owned-building table.
- `/admin/buildings`: filtered cross-owner inventory; `?building=123` opens read-only metadata/range/latest-prediction detail.

Admin links use these dedicated views rather than accidentally calling ordinary owner-only APIs. Invalid IDs show a selection error; missing IDs receive404. Loading, empty, backend/malformed-response error and Retry states are explicit. Tables scroll within their panels on narrow screens.

The existing native-fetch/ApiError architecture and Zod validate safe responses without fallback fixtures. TanStack Query admin keys start with `["admin", actingUserId, ...]`, include page/filter/detail identity, and remain separate from ordinary user caches. Queries run only for a verified ADMIN. Logout clears private query data through the existing auth provider. Status mutations invalidate the relevant admin user/overview prefix only. No routing provider or middleware is replaced.

## Verification

```powershell
.venv\Scripts\python.exe -m pytest -q
node --experimental-strip-types --test tests/frontend_*.test.mjs
node node_modules/typescript/bin/tsc --noEmit
npm run build
.venv\Scripts\python.exe tests/verify_admin_browser.py
```

The browser command uses installed Edge, existing websocket-client and dynamically available localhost ports. It runs the previous authentication, owner CRUD, measurement/CSV, readiness, forecasting/recommendation and dashboard workflows, then verifies admin counts against SQL, USER denial, cross-owner details/activity, search, pagination, deactivation confirmation/cancel, immediate existing-session revocation, blocked inactive login, retained data, reactivation and self/final-admin protections. It checks1440px/390px admin pages and malformed-response Retry. Test-only pagination accounts exist solely in the disposable verification database. It stops its own processes and removes temporary DB/profile data. Ignored evidence/screenshots remain in `ml/results/generated`.

The audit is [phase28_admin_panel.json](../ml/results/phase28_admin_panel.json). Model artifacts, feature formulas/schema, original research metrics and recommendation thresholds remain unchanged. Phase29 hardening and all automatic prediction, IoT, payments, email, savings and physical-control work remain outside this phase.
