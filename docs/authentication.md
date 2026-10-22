# Phase 22 authentication and roles

[Overview](../README.md) | [Database foundation](database-architecture.md) | [Auth audit](../ml/results/phase22_authentication_roles.json)

This phase adds actual signup/login and persistent opaque sessions to the application layer. Research methodology, numerical artifacts, model/inference/recommendation helpers and research endpoint payloads are unchanged. Public research APIs and Swagger remain available without login. Application routes require a verified session; admin routes require ADMIN but retain the honest unavailable management shell. No building CRUD, measurement/import, building-specific forecasting or admin management is implemented.

## Architecture and password handling

Browser -> host-only HttpOnly cookie -> FastAPI -> SHA-256 session-token lookup -> active User. No JWT or frontend identity storage is used. The browser's current-user state comes from `GET /auth/me`, using the existing QueryClient and native fetch. The old `sea-session` localStorage key is removed/ignored. The unused historical parser remains solely for legacy regression tests; it is not an authentication source. No password/session secret is stored in localStorage/sessionStorage.

Passwords use **Argon2id**, through `pwdlib[argon2]` and `PasswordHash.recommended()`, with random salts. Signup/bootstrap require 12-128 characters; login accepts 1-128 for verification and returns generic credential errors. Passwords are not trimmed or case-normalized. Pydantic SecretStr redacts request object representations; API validation responses omit invalid input values. Password hashes are never returned. Unknown-account verification uses a dummy Argon2 hash; no strict timing-equivalence or brute-force protection certification is claimed.

Session tokens use `secrets.token_urlsafe(32)` (32 random bytes); only their SHA-256 hex digest is persisted. Raw tokens exist transiently during issuance/request handling and are sent only through Set-Cookie, not API JSON or logs. Login/signup create a new token and revoke the current browser's previous token if supplied, preventing session fixation. Other browser/device sessions remain separate. Logout deletes only the supplied session and clears the cookie; repeating logout is safe.

## Schema and migration

[0022_authentication_sessions.py](../backend/migrations/versions/0022_authentication_sessions.py) adds `auth_sessions`: integer id, required user_id FK, unique indexed token_hash, created_at and indexed expires_at. Hash length and positive lifetime have database checks; user deletion cascades to sessions, subject to existing ownership restrictions. There is no raw token column. Existing Phase 21 migration is unchanged.

The online migration validates existing email identities before updating any row, normalizes them and refuses invalid/colliding identities with an explicit error. It does not merge accounts or change names/ownership/roles. Resolve legacy conflicts explicitly before retrying. A unique `lower(trim(email))` expression index also prevents ASCII case/whitespace duplicates from direct SQL. SQLite cannot reflect expression indexes through current SQLAlchemy/Alembic, so autogenerate/check may warn that this index is skipped; focused tests verify actual SQLite index SQL and duplicate rejection. Future migrations must preserve/review it explicitly.

Offline SQL generation cannot perform the online identity preflight/IDN conversion: its email UPDATE only lowercases/trims. Offline SQL is for inspection; prevalidate/normalize existing identities before deliberately using it on a database. Live PostgreSQL deployment is not verified in this phase. Downgrade removes sessions/index but preserves normalized email spelling; lost sessions are not reconstructed.

## Identity and roles

Email normalization trims surrounding whitespace, validates syntax with `email-validator` without DNS/deliverability lookup, converts internationalized domains to ASCII IDNA and lowercases the entire address. Non-ASCII local parts are rejected. Public signup, login and bootstrap share this policy; unrelated full_name spelling is preserved, although blank names are rejected. This treats local-part case as insensitive deliberately for account identity. There is no verification email or ownership proof of the entered address.

Public signup accepts **email/password/full_name only**, always creates active USER, hashes the password and establishes a session. Extra fields, including role/password_hash, are rejected. Duplicate email returns 409, intentionally revealing that an identity exists. ADMIN is provisioned only through the explicit local bootstrap command; frontend role values are never authorization evidence.

`get_current_user` checks token format/digest, expiration, user existence and active status on every authenticated request. `require_admin` builds on that dependency and returns 403 for USER, 401 without valid authentication. It is tested using a test-only probe; no admin management API is mounted. Inactive login is rejected with the same safe error as unknown identity/wrong password. When inactivity is observed, all that user's sessions are deleted; an existing session stops authenticating on its next request.

## Endpoints

| Method/path | Behavior |
| --- | --- |
| POST `/auth/signup` | 201 safe USER response and cookie; validation 422, duplicate 409 |
| POST `/auth/login` | 200 safe user and new cookie; generic 401 on invalid/inactive credentials |
| GET `/auth/me` | Safe id/email/full_name/role/is_active; 401 for missing/expired/revoked/inactive session |
| POST `/auth/logout` | Revoke supplied session, clear cookie, 200; idempotent |

All auth responses use `Cache-Control: no-store`. No password hash, token/hash or internal session data is included. Expired/malformed/revoked/inactive cookies are cleared on `/auth/me` failures; expired records are deleted when accessed. Missing database/migrations produce sanitized 503 errors; research startup/health do not require a database connection. Unvisited expired records can remain until future housekeeping; no background cleanup service is implemented.

## Cookie, expiry, CSRF and CORS

| Setting | Policy |
| --- | --- |
| Cookie | `smartenergy_session`; host-only, Path=/, HttpOnly=true, SameSite=Lax |
| Lifetime | Absolute lifetime, default 24 hours; `SMARTENERGY_SESSION_HOURS` integer 1-720; no sliding renewal |
| Secure | `SMARTENERGY_COOKIE_SECURE=false` locally; set `true` for HTTPS deployments |
| Frontend default API | `http://localhost:8000` |
| Local frontend | `http://localhost:5173` (also explicitly allowed localhost origins 3000/8080) |

Use **localhost consistently** in browser URLs, frontend API configuration and Swagger when demonstrating auth. Mixing frontend localhost with API 127.0.0.1 makes them different sites and can prevent SameSite cookies. Binding Uvicorn to loopback 127.0.0.1 is compatible with browser requests to localhost; hostname in the URL controls cookies. Separate unrelated frontend/API sites are not supported by this Lax-cookie setup; use a same-site deployment or reviewed reverse proxy architecture. Environment values are read by their process; restart/rebuild as appropriate.

Auth fetches use `credentials: "include"`; public research calls keep credentials omitted. FastAPI allows credentials only with explicit configured origins; override comma-separated `SMARTENERGY_CORS_ORIGINS` when changing ports. Wildcard origin entries are excluded. No frontend dependency upgrades or second HTTP/QueryClient framework are added.

Every auth POST requires `X-SmartEnergy-CSRF: 1`. This non-simple header requires a browser preflight; the backend also checks Origin against configured frontend origins or its own API origin. Missing/untrusted headers/origins receive 403. Non-browser clients may omit Origin but still need the header. Swagger exposes this header through the shared dependency. This protects authentication mutations, including login/logout; do not rely solely on SameSite or CORS, and apply equivalent protection to future cookie-authenticated mutations. This is an origin/header approach, not a synchronizer-token implementation.

## Frontend behavior

Login/signup reuse the existing AuthShell/Input/Button design. Signup has full name, email, password and confirmation with client checks; server validation remains authoritative. Neither role selection nor email verification is claimed. Forms use POST as their native fallback and are disabled in SSR until hydration attaches handlers, preventing credential submission as a URL query. Pending requests disable controls, and safe server/network errors remain visible.

A successful mutation is followed by `/auth/me`; JSON success alone cannot fake a working cookie. Login returns to an allowlisted internal intended destination (default dashboard), preventing external redirects. Logout must succeed on the server before clearing current-user/research caches and redirecting. Failed logout is reported without pretending the server session was revoked.

The shared AppShell guard protects dashboard, predictions, recommendations, data, settings, buildings and all admin routes. SSR renders a neutral session-check state, never authenticated children. The browser verifies after hydration, on route changes/window focus and every 60 seconds while foregrounded. Cached identity is suppressed on verification failures. UI expiry/inactivity visibility can therefore lag until that next check, while backend dependencies reject immediately on each request. USER receives an explicit admin-access denial; ADMIN sees navigation and the unavailable admin shell. Future private loaders/APIs must independently enforce backend dependencies; frontend guards are not authorization security for data APIs.

Public routes remain home/about/contact/login/signup and truthful password-reset/verification/setup notices. Header/settings use actual account name/email/role. Theme settings still work. No password-change, reset, email delivery, account editing or email verification service is implemented.

## Initialize and run locally

From repository root, with existing frontend dependencies:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m alembic upgrade head
# Optional, explicit first administrator; no default account is seeded:
python scripts/create_admin.py
python -m uvicorn backend.main:app --reload
```

In a second terminal:

```powershell
npm run dev -- --host localhost --port 5173 --strictPort
```

Open [signup](http://localhost:5173/signup) or [login](http://localhost:5173/login), then the dashboard. Swagger/research APIs remain public at [localhost:8000/docs](http://localhost:8000/docs). The database is ignored by Git; never commit it or runtime credentials. A verified model artifact is still needed for research panels.

The bootstrap prompts for email/name and uses getpass twice for password/confirmation; it refuses echoed fallback input when a secure prompt is unavailable. No password CLI argument, hardcoded credentials or automatic admin is provided. Existing identities are rejected without promotion/overwrite. Use an interactive terminal and initialize migrations first.

## Verification and boundaries

The audit environment already has pytest; it is a test tool, not a new authentication runtime dependency. Provision pytest separately in a fresh test environment, or use the existing unittest-compatible suite with `python -m unittest discover -s tests -p "test_*.py"`. Browser QA additionally needs installed Edge and websocket-client as in the earlier reproduction notes.

```powershell
python -m pytest
node --experimental-strip-types --test tests/frontend_api.test.mjs tests/frontend_auth.test.mjs
npm run build
node node_modules/typescript/bin/tsc --noEmit
python tests/verify_auth_browser.py
```

Backend tests override sessions with disposable migrated SQLite databases and generate credentials at runtime. Migration tests exercise fresh head, Phase21 upgrade preserving ownership, and explicit refusal of colliding legacy identities. Browser QA uses dynamic localhost ports and a disposable database/profile, bootstraps an ADMIN through the same CLI core function, drives real forms/cookies, checks refresh/backend-restart persistence, logout, role guards and inactive/expired sessions, then cleans its processes/data. Existing CDP helper definitions are reused without invoking the historical unauthenticated browser scenario. The old standalone Phase18 browser script describes a pre-auth workflow; use the Phase22 verifier for current application routes.

Limitations: no MFA, rate limiting, lockout, email ownership verification, password reset/change, session-management UI or scheduled expired-session cleanup; no security certification. Duplicate signup intentionally returns 409. Use HTTPS and Secure cookies before deployment, explicitly configure trusted origins, review proxy/host handling and add operational security controls. SQLite concurrency and unpinned environment limits remain. Accounts/roles do not establish multi-building model validity or operational building services.

References: [FastAPI password hashing with pwdlib](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#password-hashing) (only hashing guidance; this implementation uses no JWT), [OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [OWASP CSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).
