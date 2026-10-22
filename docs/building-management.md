# Phase 23 building management and ownership

[Overview](../README.md) | [Authentication](authentication.md) | [Database foundation](database-architecture.md) | [Phase audit](../ml/results/phase23_building_management.json)

Authenticated users can create, list, view, edit and delete persisted building metadata. This reuses the existing Building table and User ownership relationship. No columns, migrations or dependencies were added; the schema head remains `0022_authentication_sessions`. Earlier phase documents describe their historical scope.

## Ownership and ADMIN policy

**All roles are owner-only in this phase.** The server takes owner_id exclusively from the active authenticated User. USER and ADMIN lists contain only their own buildings; detail/update/delete query both id and owner_id. Non-owned and nonexistent resources return the identical **404 Building not found** response. ADMIN cannot inspect, edit or delete another user's building here. Broader administrative access belongs to a separately authorized admin phase, not an implicit bypass.

Requests cannot set id, owner_id, created_at or updated_at. Extra fields are rejected. Responses contain metadata only, without owner email, account details, ownership identifiers, child records or ORM internals. Every operation depends on the existing active-user/session validation. No frontend role or owner value grants access.

## API and validation

| Method/path | Behavior |
| --- | --- |
| POST `/buildings` | Create for current owner; 201 metadata response |
| GET `/buildings` | `{ "buildings": [...] }`, owner-only, ascending integer id order |
| GET `/buildings/{building_id}` | Owner metadata; missing/non-owned 404 |
| PATCH `/buildings/{building_id}` | Partial metadata update; 200 confirmed persisted response |
| DELETE `/buildings/{building_id}` | Delete owner building and cascade children; empty 204 |

All requests include the existing HttpOnly session cookie. POST/PATCH/DELETE require `X-SmartEnergy-CSRF: 1` and the existing trusted-Origin checks. Credentialed CORS explicitly permits GET/POST/PATCH/DELETE for configured origins; wildcard credentialed origins are excluded. Reads and writes/errors under `/buildings` use `Cache-Control: no-store`. Research endpoints remain public and retain their payloads. A missing database/schema produces a sanitized application database error, not a mock response.

| Field | Contract |
| --- | --- |
| name | Required on create; trimmed, 1-200 characters; cannot be null/blank |
| building_type | Optional/null; Residential, Office, Educational, Healthcare, Retail, Industrial or Other |
| floor_area_m2 | Optional/null; strict numeric, finite and >0; booleans/numeric strings/NaN/infinities rejected |
| city | Optional/null; trimmed, at most 200 characters; blank becomes null |
| description | Optional/null; at most 4,000 characters; text otherwise preserved |

PATCH distinguishes omitted fields (preserved) from explicit null (clears optional metadata). Name cannot be cleared; an empty PATCH is rejected. Invalid input returns 422. Existing ORM defaults manage naive UTC created_at/updated_at timestamps; fields cannot be edited by clients. No intervention evidence or physical range clipping is invented. Building types remain strings in the existing table with controlled API validation. Direct unvalidated database writers must honor this API contract; legacy unknown type/text values may need explicit correction before serving through these schemas.

A small [service](../backend/building_service.py) owns the scoped SQLAlchemy queries and commit/refresh operations. The dedicated [router](../backend/buildings.py) wires schemas, authenticated session and CSRF dependencies. [Schemas](../backend/building_schemas.py) explicitly allowlist editable/returned fields. No generic repository framework or admin filtering was introduced. Lists currently return all owner rows, ordered by id; pagination is a future scalability concern.

## Deletion

Building deletion deliberately uses Phase 21's `ON DELETE CASCADE` for associated Measurements and Predictions; user ownership is never reassigned. The UI requires a separate confirmation and explains that any associated history stored now or later would also be deleted. Cancel leaves the building unchanged. Deletion is permanent; no soft-delete/archive/restore workflow is implemented. Tests verify the API cascade using test-only child rows in a disposable database, without adding measurement/prediction endpoints or importing research observations into the application DB.

## Frontend

The existing `/buildings` list and `/buildings/$id` detail route files are reused. No new route file or manual generated-tree edit is needed. The mock loader, charts, savings, sensors and occupancy values were removed from these two routes. The shared authenticated AppShell now permits building management while retaining unavailable notices for data/admin management.

- List: actual name/type/city/area cards, `Loading buildings...`, explicit errors/Retry and **No buildings yet**. Add building opens a real form. No example/reference building is seeded.
- Create: required name and optional type/area/city/description; submit waits for server confirmation, then opens its returned id. Native POST fallback and hydration-disabled controls prevent unintended early submissions.
- Detail: actual metadata and UTC audit timestamps. Missing, invalid or non-owned ids show the same not-found explanation. No fake operational metrics or child counts are computed.
- Edit: persisted values populate the same form; PATCH confirmation updates detail/list caches. Validation/network errors preserve entered values. Cancel closes without a write.
- Delete: separate confirmation, cascade warning and Cancel. Successful empty204 is handled by the existing transport and redirects to the updated list.

[Typed API functions](../src/lib/api/buildings.ts) use existing native fetch/ApiError with included credentials, CSRF mutation headers, strict response parsing and no fallback values. The transport gained explicit successful204 handling, while malformed200 JSON remains an error. [Hooks](../src/hooks/use-buildings.ts) use the existing QueryClient with keys partitioned by user id and route building id. Mutations have no automatic retry or optimistic success: confirmed responses update detail data, invalidate the owner list and remove deleted detail cache entries. 401 triggers current-session revalidation; all authorization remains server-enforced.

Building identity comes solely from the route. No hidden global selected-building state exists. Logout already clears private query caches, and per-user keys isolate a different account even without a full browser restart. Query errors take precedence over old cached data. Background authentication rechecks now preserve an already-verified view instead of unmounting an active form; initial loading still blocks it, and verification errors/401 still hide protected content. The live verifier checks a draft survives an actual background `/auth/me` request.

## Scope and research domain

Detail shows **Measurement data has not been configured yet**, with no fabricated count or chart history. This means the measurement capability is not implemented; it is not a database assertion that a count was queried. Measurement entry/import, feature construction from history, building-specific prediction and prediction/recommendation persistence endpoints remain unavailable.

A later import phase can introduce a clearly labeled **UCI Reference Building** and its historical observations. None is created or assigned here. The final model was validated on the research reference dataset; **creating a building or choosing a building type does not establish model validity for that building**. Metadata is not added to the fixed 42-feature contract. No model execution is required for building CRUD, and no retraining/tuning/held-out evaluation occurs.

## Run and verify

Use the existing startup workflow:

```powershell
.\.venv\Scripts\Activate.ps1
python -m alembic upgrade head
python -m uvicorn backend.main:app --reload
```

In another terminal, `npm run dev -- --host localhost --port 5173 --strictPort`. Use localhost consistently for cookies, sign in, then open [Buildings](http://localhost:5173/buildings). No database migration beyond the existing head is required.

```powershell
python -m pytest
node --experimental-strip-types --test tests/frontend_api.test.mjs tests/frontend_auth.test.mjs tests/frontend_buildings.test.mjs
node node_modules/typescript/bin/tsc --noEmit
npm run build
python tests/verify_buildings_browser.py
```

Tests use existing pytest/native Node tools, not new runtime dependencies. Backend tests override database sessions with migrated temporary SQLite files. The browser verifier extends the existing isolated auth scenario, uses runtime-generated credentials/dynamic ports, and cleans all its own processes, database and profile. It verifies User A create/list/view/edit/refresh/restart/delete, User B direct URL/API denial and independent building, and the owner-only ADMIN policy. The complete signup/session/logout/admin/inactive/expired/CSRF research regression runs alongside it. Logs/screenshots stay ignored.

Limitations: unpaginated owner list, no concurrent-edit conflict detection, no soft delete, no cross-owner admin tools, and no measurement/prediction capability. Existing authentication/deployment/SQLite limitations remain; this is not a production security certification or multi-building forecasting validation. No local developer database, dependencies, previous migrations or numerical research artifacts are changed by verification.
