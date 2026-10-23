# Final route and API inventory

[Overview](final-application-overview.md) | [Swagger](http://localhost:8000/docs)

Generated from current FastAPI OpenAPI methods/paths and inspected TanStack file routes. Query parameters/filter defaults and body schemas remain in OpenAPI and domain docs. Route classifications describe intended access; AUTH and public setup pages are reachable without authentication. USER pages also allow ADMIN with its ordinary owner scope.

## Frontend routes

| Class | Route | Behavior |
| --- | --- | --- |
| PUBLIC | `/` | Public information/setup |
| PUBLIC | `/about` | Public information/setup |
| PUBLIC | `/contact` | Public information/setup |
| PUBLIC | `/onboarding` | Public information/setup |
| AUTH | `/login` | Real signup/login |
| AUTH | `/signup` | Real signup/login |
| AUTH | `/forgot-password` | Explicit unsupported email/reset service |
| AUTH | `/reset-password` | Explicit unsupported email/reset service |
| AUTH | `/verify-email` | Explicit unsupported email/reset service |
| USER | `/dashboard` | Authenticated owner-scoped application |
| USER | `/buildings` | Authenticated owner-scoped application |
| USER | `/buildings/$id` | Authenticated owner-scoped application |
| USER | `/data` | Authenticated owner-scoped application |
| USER | `/predictions` | Authenticated owner-scoped application |
| USER | `/recommendations` | Authenticated owner-scoped application |
| USER | `/settings` | Authenticated owner-scoped application |
| ADMIN | `/admin` | ADMIN only; dedicated cross-owner oversight |
| ADMIN | `/admin/users` | ADMIN only; dedicated cross-owner oversight |
| ADMIN | `/admin/buildings` | ADMIN only; dedicated cross-owner oversight |

`$id` is the dynamic building ID; index routes may normalize a trailing slash. `__root.tsx` is layout, not an additional page. Legacy mock helpers are unused operational code, not reachable mock routes.

## OpenAPI operations

### public/research

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Root |
| GET | `/health` | Health |
| GET | `/model/info` | Model Info |
| POST | `/forecast` | Forecast |
| POST | `/forecast/recommendation` | Forecast Recommendation |
| GET | `/recommendations/thresholds` | Recommendation Thresholds |
| GET | `/analysis/model-comparison` | Model Comparison |
| GET | `/analysis/feature-importance` | Feature Importance |

### authentication

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/signup` | Signup |
| POST | `/auth/login` | Login |
| GET | `/auth/me` | Current User |
| POST | `/auth/logout` | Logout |

### buildings

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/buildings` | Create |
| GET | `/buildings` | Listing |
| GET | `/buildings/{building_id}` | Detail |
| PATCH | `/buildings/{building_id}` | Update |
| DELETE | `/buildings/{building_id}` | Delete |

### measurements

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/buildings/{building_id}/measurements` | Create |
| GET | `/buildings/{building_id}/measurements` | Listing |
| DELETE | `/buildings/{building_id}/measurements/{measurement_id}` | Delete |
| POST | `/buildings/{building_id}/measurements/import` | Import Csv |

### readiness

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/buildings/{building_id}/prediction-readiness` | Readiness |

### predictions

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/buildings/{building_id}/predictions` | Create |
| GET | `/buildings/{building_id}/predictions` | Listing |

### dashboard

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/buildings/{building_id}/dashboard-summary` | Summary |

### admin

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/admin/overview` | Overview |
| GET | `/admin/users` | Users |
| GET | `/admin/users/{user_id}` | User Detail |
| PATCH | `/admin/users/{user_id}/status` | Status |
| GET | `/admin/buildings` | Buildings |
| GET | `/admin/buildings/{building_id}` | Building Detail |
| GET | `/admin/predictions` | Predictions |

Swagger `/docs`, `/redoc` and `/openapi.json` are framework documentation routes, outside the OpenAPI operation list. Public research forecast POSTs accept 42 engineered values and do not persist operational predictions. Private forecast POSTs accept no engineered feature payload; they use owned stored history. Private mutations require the existing CSRF/origin policy. Public response schemas omit password_hash, token_hash and feature_snapshot_json; request passwords remain intentional write-only inputs. Model/feature hashes returned in prediction responses identify research/input versions and are not authentication secrets.
