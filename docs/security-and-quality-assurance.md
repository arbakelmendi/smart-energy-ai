# Full-stack security and quality assurance (Phase 29)

This is an evidence-based local prototype audit, not security certification or a production deployment assessment. See the [phase audit](../ml/results/phase29_fullstack_hardening.json) for actual gate counts, defects, protected hashes and evidence. No product feature, model, feature formula, threshold, schema migration or dependency is added.

## Defects and minimal corrections

1. **Login/deactivation race:** login read an active account before password verification/session creation. If an admin deactivated it during that interval, login could still persist a new token after all earlier sessions had been revoked; reactivation could make that token usable. A deterministic paused-login test reproduced200 instead of401. Session issuance now performs an atomic guarded no-op active-user UPDATE inside the same transaction as session creation. It acquires SQLite's write lock; a preceding deactivation causes401, while a following deactivation removes the just-issued session. Account updated_at is preserved by the guard. Signup retains its existing transactional user/session creation.
2. **Request deadline bypass:** passing a TanStack Query cancellation signal replaced the transport timeout, leaving stalled requests unbounded. A never-completing fetch fixture reproduced it. Native AbortSignal.any now combines caller cancellation with the10-second deadline. CSV import explicitly retains its120-second deadline. Cancellation still propagates, including while reading response JSON; timeout failures become controlled ApiError messages. Seven older tests now check cancellation propagation rather than object identity.
3. **Unnamed mobile navigation close button:** the existing icon-only close action lacked an accessible name. It now has `aria-label="Close navigation"`; browser verification checks that action and ordinary Tab navigation through a form.

4. **Obsolete setup guidance:** the legacy onboarding page incorrectly said building registration was unavailable after owned-building management had been implemented. It now describes the existing metadata/manual-CSV workflow and links to Buildings, without adding a wizard or sensor connection. Recovery/verification copy also now distinguishes unsupported email services from the real authentication and admin activation services.

5. **Verifier-induced page reloads:** Edge profiles were stored below the Vite-watched repository. Logs showed Edge Wallet HTML files triggering unrelated client reloads. Profiles now use a validated OS temporary directory outside the repository; ignored evidence remains under generated/. This fixes QA interference, not application behavior.

6. **Ambiguous test form selector:** the shared helper used a document-wide name selector, so the description fixture could update a head metadata element instead of the textarea. It now selects form controls. A focused browser smoke test confirms all four marker fields through the API and checks the description-specific owner/admin DOM nodes as text.

7. **Private files served by Vite:** a harmless probe reproduced unauthenticated200 responses containing bytes from SQLite-named files and generated QA logs. Git ignore rules do not protect HTTP access. The existing Lovable wrapper now receives a narrowly scoped server.fs.deny extension preserving installed Vite defaults and blocking local SQLite/sidecars, generated QA files, backend source and the Python environment. The probe verifies direct/raw/URL-import/absolute-fs forms using only its own harmless files, plus normal page/client-module access. No real operational DB is read.

Only affected behavior is changed. No authentication infrastructure, global lock service, new routes, package upgrades or UI redesign is introduced.

## Authentication, cookies and sessions

Password hashing remains Argon2id with random salt through existing pwdlib. Passwords are not trimmed, case-normalized, stored in browser identity storage, or returned in JSON. Existing validation enforces name/email/password policy and rejects public role assignment. Normalized duplicate email checks are backed by a DB expression uniqueness index. Unknown/wrong/inactive login uses the same safe error. Tests also race two normalized-equivalent signups: one201 and one409, one account.

The browser receives a random opaque43-character token in the host-only `smartenergy_session` cookie; the DB stores only a unique 64-character SHA-256 digest. HttpOnly, SameSite=Lax and Path=/ are verified. Secure=false supports local HTTP; `SMARTENERGY_COOKIE_SECURE=true` is tested with HTTPS. Expiry is checked server-side, and expired/revoked/inactive tokens cannot authenticate. Multiple sessions are supported. Login rotates the current browser's token, logout revokes that token only, and admin deactivation revokes every target session. Reactivation does not restore old tokens. Valid sessions survive backend restart because their hashes remain in the DB.

Issuance/status writes are now serialized as described above. This does not cancel requests already authorized before revocation, nor provide real-time websocket logout. Idle clients learn revocation at their next request, navigation/focus revalidation or existing60-second auth check. Two real browser tabs verify that logout in one makes the other tab's next protected action fail and redirect safely.

## CSRF and CORS

The established policy is a fixed non-simple `X-SmartEnergy-CSRF: 1` header plus explicit Origin validation, not a secret per-session nonce. Cross-session nonce comparison is therefore inapplicable: the header is deliberately the same across sessions. Missing/wrong headers and untrusted origins are tested against state-changing auth, building, measurement/import, forecast and admin-status operations; no denied mutation changes state. Authenticated identity/ownership checks remain independent.

CORS permits explicit configured localhost frontend origins with credentials and the required methods/headers. Wildcard configuration entries are excluded. Real preflights verify an allowed origin and reject untrusted/opaque origins. An untrusted actual mutation is denied too. A CLI request without Origin may use the valid header and cookie; this is the documented native-client policy, not origin authentication. Public research GETs and stateless generic forecast POSTs remain intentionally public; those POSTs do not mutate account/domain data. Restart services after changing startup CORS configuration.

## Authorization matrix

| Resource/action | Anonymous | USER owner | USER other owner | ADMIN ordinary app | Dedicated ADMIN API |
| --- | --- | --- | --- | --- | --- |
| Public research results/inference | Public | Public | Public | Public | Public |
| `/auth/me` |401 | Own identity | Own identity | Own identity | Own identity |
| Normal buildings/history/readiness/predictions/dashboard |401 with valid CSRF where needed | Allowed |404 | Own buildings only; foreign404 | Not a bypass |
| `/admin/overview`, users, buildings, predictions |401 |403 |403 | ADMIN required | Cross-owner oversight allowed |
| Admin status PATCH |401 |403 |403 | ADMIN + CSRF | Protected activation/deactivation |
| Logout with valid CSRF | Idempotent | Current token only | Current token only | Current token only | Current token only |

Mutation requests without valid CSRF can be rejected403 before ordinary ownership handling; this is not a data disclosure. The admin router checks authentication server-side on every endpoint. Direct-ID attacks substitute building and measurement IDs across GET/POST/PATCH/DELETE/import paths, including a measurement placed under the wrong owned building. USER B and a second ADMIN cannot read or mutate foreign ordinary resources. Only dedicated admin APIs allow cross-owner oversight.

Admin self-deactivation and final-active-admin deactivation remain blocked. Simultaneous mutually targeted deactivation persists one active admin. Admin status and all-session deletion roll back together on injected commit failure. Role mutation, user deletion and password reset have no supported admin endpoint. Safe schemas exclude password/session hashes, raw cookies and feature snapshots. Reference ownership is unchanged.

## Validation, uploads and SQL safety

Existing strict schemas reject malformed names/emails/passwords, unknown fields, unsupported building types, nonpositive/nonfinite area, missing/nonfinite raw readings, timezone-offset timestamps and invalid pagination. The full old suite remains part of this audit. New CSV cases cover empty/header-only/non-UTF8 files, duplicate/missing/extra headers, duplicate timestamps, DB collisions, NaN/infinity, malformed numbers/offset timestamps and oversized payloads. Every failed import leaves the destination unchanged. A real HTTP upload of all19735 UCI rows succeeds, with rv1/rv2 ignored as documented.

Uploads retain the existing16MiB/25000-row limit and500-row DB batches. No new limit blocks the UCI source. The endpoint bounds the read and validates before writing; multipart parsing/spooling can precede that endpoint guard, so a production reverse-proxy total-body limit is still advisable. No rate-limiting/upload gateway is added.

User-controlled search/filter/IDs use SQLAlchemy parameters. The only interpolated table identifiers in migration QA come from a fixed internal list, never request input. Admin substring search escapes SQL wildcard characters; SQL-injection-like strings are tested literally. User full name, building name/city/description render through React text nodes. A live `<img ... onerror=...>` marker remains text in ordinary and admin views and never creates an image or executes code. The scaffold chart component's static configuration CSS injection is not fed account/building content; it is not a user HTML renderer.

## Migrations, constraints and transactions

Actual lineage is `0021_database_foundation -> 0022_authentication_sessions -> 0026_prediction_feature_snapshots`, with one head. New isolated tests start with zero tables and also upgrade populated Phase21/22 schemas. Repeated upgrade is safe; Alembic current/heads agree with the DB revision, and resulting metadata matches current models. Pre26 predictions retain values and nullable absent feature snapshots, without invented data. SQLite cannot reflect the normalized email expression index through current Alembic, so direct index/duplicate-write tests supplement metadata comparison. No historical migration is edited.

The suite checks SQLite foreign_keys=ON, unique normalized email, unique building/timestamp measurement, finite/positive constraints, unique session digest, unique semantic prediction identity and complete snapshot pairs. User deletion restrictions and building/session child cascades are tested only in disposable DBs. Injected signup/session, CSV late-batch, prediction-commit and admin-status failures verify rollback. DB errors use sanitized503 responses; unexpected errors use generic500 responses. API responses do not expose test fault SQL, private paths, traceback or credential strings. Developer diagnostic logs are not a public API.

## Concurrency, features and inference

SQLite-backed tests cover duplicate signup, duplicate measurements, multiple sessions/logout/deactivation, concurrent final-admin operations and identical forecast idempotency. A deleted parent during measurement insertion or inference fails safely without orphan records. Historical feature corrections create distinct fingerprinted forecasts; old versions remain historical, and restoring exact inputs can recover a prior matching snapshot beyond the recent preview.

Readiness regression covers0/1/1008/1009 observations, gaps inside/outside the required window, out-of-order insertion, deletion/restoration and a new latest20-minute gap. Phase25 parity rechecks all42 ordered features at representative TRAIN/VALIDATION origins and the reference latest prefix with the original1e-10 absolute float64 tolerance. Its export is regenerated **only in a temporary directory** for byte comparison; committed research artifacts are untouched. Production inference and authoritative Phase14 recommendation snapshots are compared through the existing verification helpers. No tuning, selection or held-out metric evaluation is performed.

Missing/corrupt model behavior is simulated by loader faults without touching the real artifact. No fallback forecast is returned or persisted; history/measurement/admin reads continue where supported. Full protected datasets, model, feature schema/math, notebooks, old results/audits, migrations, route tree and package files are hashed before/after QA.

## Frontend reliability and browser coverage

Private Query keys include authenticated identity, building/administrator, page/filter/window as applicable. Logout cancels and removes private queries. Existing native tests validate malformed auth/building/measurement/readiness/prediction/dashboard/admin responses without fixture fallback and exercise account/building cache invalidation. The browser checks account switching, foreign deep links, and real USER/ADMIN journeys. A separate fresh account completes manual entry + nonoverlapping CSV + readiness + forecast + recommendation entirely through supported UI/APIs, without manual domain DB edits. Earlier security regression callbacks use explicit temporary DB fixtures for faults/expiry/role races; those are tests, not application prerequisites.

The backend is actually stopped while the frontend remains open: current forecast/recommendation disappears into a controlled unavailable state, observed failed requests do not form an immediate loop, and Retry after restart recovers the same stored prediction. Refresh/restart checks rebuild dashboard, building, ledgers and admin data from persistence. All19 reachable route patterns are visited as anonymous, USER and ADMIN, including deliberate denial/not-found states rather than blank screens.

Desktop1440px/mobile390px coverage includes auth, building forms/list/detail, measurement/import, dashboard/chart/forecast and admin pages. Tables scroll inside panels. Labels, keyboard Tab behavior, critical button naming, readable error/status text and heading presence receive a limited sanity check. This is not a WCAG or screen-reader certification. HTTP API/SSR security headers are recorded as observed; development error diagnostics may still reveal project paths and the dev server must not be treated as a public production host; no complex CSP or middleware rewrite is added, and development headers are not a production policy guarantee.

## Reproduce and inspect evidence

Use the existing installation in [reproducibility](reproducibility.md), then run from repository root:

```powershell
.venv\Scripts\python.exe -m pytest -q
node --experimental-strip-types --test tests/frontend_*.test.mjs
node node_modules/typescript/bin/tsc --noEmit
npm run build
.venv\Scripts\python.exe tests/verify_feature_parity.py
.venv\Scripts\python.exe tests/verify_building_predictions.py
.venv\Scripts\python.exe tests/verify_fullstack_browser.py
.venv\Scripts\python.exe tests/verify_auth_browser.py --hardening-smoke
.venv\Scripts\python.exe tests/verify_dev_file_access.py
git diff --check
```

The browser requires installed Edge, existing websocket-client and available dynamic localhost ports. It migrates disposable SQLite, uses supported administrator bootstrap, blocks external page requests and removes its temporary DB/profile/processes afterward. Evidence/screenshots/logs are ignored in `ml/results/generated`. The phase audit records the exact semantic-lint target list; formatting debt is not mass-cleaned.

## Secret/path, dependency and prototype limits

Lightweight source/built-JS scans detect obvious token/private-key formats and credential URLs, not every possible secret. Runtime QA also checks its passwords and a sample session token against local QA logs. Tracked operational databases, raw/processed datasets, generated QA artifacts and ignored model files must remain excluded from staging. See the audit for actual scan findings.

Four pre-existing historical artifacts contain machine-specific output paths: Phase7/8/9 validation JSON `results_path` values and one baseline notebook output. They are provenance/output strings, not required runtime configuration; their protected research bytes are deliberately preserved and the findings are disclosed rather than rewritten. New Phase29 documentation/results use relative paths.

No dependency is added or upgraded. Existing Python requirements remain partly unpinned and combine research/notebook/test/server needs; frontend ranges and the existing Bun lock remain intact. This audit verifies the installed environment, not arbitrary future library combinations. It does not certify absence of all package vulnerabilities.

Remaining limits: no rate limiting, MFA, OAuth, email verification/reset delivery, centralized audit log, production deployment hardening/certification, IoT authentication model or real-time session push. SQLite serializes writes and is not a production concurrency guarantee; live PostgreSQL is unverified. Offset pages can move during concurrent writes. HTTPS/cookie/proxy/security-header policy requires deliberate deployment configuration. There are no savings, confidence intervals, scheduler or physical controls. Phase30 remains separately authorized work.

## Final release verification (Phase30)

[Final overview](final-application-overview.md), [release inventory](final-endpoint-inventory.md) and [demo checklist](final-demo-checklist.md) describe the current application. Phase29's audit JSON remains unchanged. Phase30 additionally verifies a tracked-file isolated copy, separately installed Python/frontend dependencies, no copied operational DB/session state and the supported reference-import command. The release browser verifier is `python tests/verify_final_application.py`; it performs supported UI/API operations only after empty migration/bootstrap, with disposable runtime credentials and cleanup.

Two fresh-setup regressions were corrected without weakening security/research guards: `.gitattributes` keeps byte-checksummed `ml/results/*.json` at committed LF despite Windows autocrlf, and the root error callback accepts `unknown` to match newly resolved TanStack error types. The root layout, providers, middleware and error behavior are preserved. Preflight now checks full-stack prerequisites without requiring processed TRAIN data, connecting to the DB, fitting, repairing or printing credential-bearing configuration. Missing prerequisites and private invalid configuration have explicit regressions. About/OpenAPI copy now distinguishes public engineered-feature requests from private server-built features.

Read-only preflight is not proof of DB migrations/accounts or production security. Explicit migrations, hidden-password ADMIN bootstrap and live sign-in remain separate evaluator steps. Dependency ranges can resolve newer libraries; fresh-install success is evidence for the recorded Phase30 environment, not a promise for all future versions. No penetration-testing certification, rate limiting, MFA or production security claim is added.

The final build scan also finds absolute source `filePath` provenance in the ignored server-only TanStack route manifest. Public client bundles and new release documentation contain none. Generated build output is not staged; this is disclosed as a deployment/packaging limitation, not edited out of framework output or represented as production path-exposure certification.
