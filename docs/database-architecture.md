# Final application database architecture

[Overview](../README.md) | [Architecture](system-architecture.md) | [Authentication](authentication.md) | [Forecast lifecycle](building-predictions.md)

SQLAlchemy 2 and Alembic persist real accounts/sessions, owned buildings, observed raw measurements and model/recommendation snapshots. SQLite is the local default, not a production concurrency guarantee. PostgreSQL-compatible types/migration SQL do not establish live PostgreSQL deployment support; select/install a driver separately for that deployment.

`DATABASE_URL` defaults to `sqlite:///./smartenergy.db`. Relative SQLite paths resolve against repository root. Importing engine definitions does not connect/create tables; explicit migration creates the empty database. SQLite foreign keys are enabled per connection and requests own short-lived sessions with explicit commit, exception rollback and close. Research endpoints remain database-independent. Connection credentials never belong in docs/source/logs.

## Current tables and constraints

| Table | Stored fields / constraints |
| --- | --- |
| `users` | id, normalized unique email, salted password_hash, full_name, USER/ADMIN role, is_active, created_at/updated_at; unique lower(trim(email)) expression index and role/boolean checks |
| `auth_sessions` | id, user_id, unique 64-character SHA-256 token_hash, created_at/expires_at with positive lifetime; expiry/user indexes; no raw token field |
| `buildings` | id, owner_id, name, optional building_type/floor_area_m2/city/description, audit timestamps; finite positive optional area |
| `measurements` | id, building_id, naive-local timestamp and all 26 finite raw numeric values; unique(building_id,timestamp), owner/time retrieval indexes; no future target/precomputed ML columns |
| `predictions` | id, building_id, source_timestamp, prediction_wh, horizon_minutes, model_name/checksum, feature_hash, feature_snapshot_json, created_at, recommendation_level/code/priority/text; finite output, positive horizon,64-character checksums, complete snapshot/recommendation pairing |

Prediction uniqueness is `(building_id, source_timestamp, model_checksum, feature_hash)`, not source time alone. Phase26 writes both snapshot/hash; legacy pre26 rows retain both NULL and remain historical rather than pretending to be reproducible current input. Recommendation fields are all populated or all NULL. Forecast target time is derived from source+horizon rather than an invented extra stored table/column.

Users own buildings; deleting a user with buildings is RESTRICTed. User deletion cascades sessions. Building deletion cascades measurements/predictions. Account deactivation is not deletion: it retains domain history and revokes sessions. Ordinary APIs enforce owner scope even for ADMIN; dedicated admin APIs inspect cross-owner data. ORM collections use lazy="raise" to avoid accidental unbounded loading; services use explicit paginated queries. Exact definitions: [models](../backend/db_models.py), [admin](admin-panel.md).

## Measurement semantics and validation

The cleaned dataset header and first 26 inputs of the committed [feature schema](../ml/results/feature_schema.json) define the raw contract:

| Columns | Units/meaning |
| --- | --- |
| `Appliances`, `lights` | Wh per observed ten-minute interval; lights is not occupancy |
| `T1` through `T9`, `T_out`, `Tdewpoint` | Degrees Celsius; T6 is outdoor/weather context |
| `RH_1` through `RH_9`, `RH_out` | Relative humidity percent; RH_6 is outdoor context |
| `Press_mm_hg` | mm Hg |
| `Windspeed` | m/s |
| `Visibility` | km |

Names/case are preserved exactly. Source `date` becomes `timestamp`; the final model target remains next-step Appliances Wh. See [provenance/units](../data/raw/README.md) and [feature implementation](../ml/src/feature_engineering.py). Raw rows alone do not satisfy the 42-feature inference contract: the implemented feature service establishes continuity and sufficient historical lags/rolling windows without future observations. Schema uniqueness does not prove interval continuity or cross-building model validity.

Observation/source timestamps use naive datetimes in a consistent source clock. UCI timezone is not established, so this phase does not invent a UTC conversion. Application DTOs reject timezone-aware observation timestamps; direct ORM/SQL writers must follow the same convention. Audit created_at/updated_at timestamps are naive UTC, supplied by ORM defaults; updated_at advances on ORM updates. Direct SQL writers must supply required audit times and explicitly update updated_at; no cross-database timestamp triggers are claimed.

`FiniteFloat` rejects booleans, strings, NaN and infinities on bound ORM/Core writes. Required measurement/prediction columns have NOT NULL plus finite double-range SQL checks; optional area has positive/finite checks. Pydantic DTOs also reject nonfinite values. SQLite's raw driver converts a NaN bound outside these application types into SQL NULL: required numeric fields reject it, but NULL remains legitimate for optional floor area. Therefore future application writes must use validated DTOs/ORM types, not arbitrary driver SQL. Physical range clipping is not imposed: environmental values can be negative, and persisted model output is not silently clipped. No data-quality/comfort assumptions are invented.

## Initialization and migration lineage

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic heads
python scripts/create_admin.py
```

The single head is `0026_prediction_feature_snapshots`, following `0021_database_foundation` then `0022_authentication_sessions`. No accounts/buildings/history are seeded; ADMIN bootstrap is an explicit hidden-password workflow. The Phase22 migration validates/normalizes legacy email identities and refuses invalid/colliding ones without silently merging. Phase26 preserves legacy prediction values while adding nullable input snapshots and semantic uniqueness. Do not edit old migrations or drop real DBs to repair setup.

Fresh, populated Phase21 and populated Phase22 upgrades, repeated upgrade, metadata/constraints/index checks and legacy preservation are verified by [migration tests](../tests/test_migration_hardening.py). SQLite expression-index reflection emits an existing warning; focused tests inspect the actual normalized-email index. PostgreSQL offline SQL is inspection only, not proof of a working live service.

The ignored DB/sidecars are operational state, never release artifacts. Back up real data before upgrading. Downgrade destroys some state and belongs only in disposable verification DBs. SessionLocal/get_db never auto-commit response lifecycles. `/health` checks research/model resources, not migration/account readiness; use explicit Alembic commands and login to verify those.
