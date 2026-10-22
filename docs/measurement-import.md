# Building measurements and CSV import (Phase 24)

Measurements are raw timestamped observations owned through a Building. They are persisted independently of the research API. No ingestion path constructs the 42 features, invokes the model, creates Prediction records, or stores recommendations. A new building and a measurement count do not establish model validity or ML readiness.

## Schema and units

The existing Measurement table is unchanged: id, building_id, timestamp, and exactly 26 required finite numeric fields:

- Energy: Appliances, lights (Wh per observation interval; the UCI reference interval is ten minutes). These are energy, not instantaneous power; lights is not occupancy.
- Temperature: T1 through T9, T_out, Tdewpoint (degrees Celsius).
- Relative humidity: RH_1 through RH_9, RH_out (%).
- Pressure: Press_mm_hg (mm Hg); Windspeed (m/s); Visibility (km).

Units come from [existing project provenance](../data/raw/README.md). T6/RH_6 are outdoor observations, so the form groups them with weather. Sensor labels are preserved; no new sensor-location or occupancy meaning is inferred. Storage enforces finiteness rather than invented plausibility ranges. All 26 fields are mandatory; unknown observations must not be filled with fabricated defaults. JSON numeric strings, booleans, NaN and infinities are rejected.

## Timestamp policy

Measurement timestamps are **timezone-naive building-local observation times**, distinct from account/building audit timestamps (naive UTC). API JSON accepts ISO-8601 date and time without timezone, such as the structural format `YYYY-MM-DDTHH:mm:ss`; the UCI space separator is also accepted. Date-only values, numeric epochs, offsets and Z are rejected. Fractional seconds are retained to microsecond precision. No browser/server timezone conversion occurs.

This preserves the original UCI timestamp semantics without inventing a timezone. Cross-building absolute-time comparisons and daylight-saving ambiguity cannot be resolved with this schema. Duplicate timestamps are compared after parsing, including equivalent space/T or fractional representations. Valid arbitrary intervals may be stored. Future inference will require verified continuous compatible ten-minute history; row count alone is insufficient, and Phase 25 must check continuity and required lags.

## API and ownership

All routes require an active cookie-backed session and an owned Building. USER and ADMIN follow the same owner-only policy. Building lookups return uniform404 for missing/non-owned IDs; a measurement delete also checks its building_id. Owner/building IDs cannot be supplied in the body. Mutation routes require the existing `X-SmartEnergy-CSRF: 1` and trusted-origin rules. All building/measurement responses remain no-store.

| Endpoint | Result |
| --- | --- |
| POST /buildings/{id}/measurements | 201, saved measurement including server IDs |
| GET /buildings/{id}/measurements?limit=100&offset=0 | 200, items/total/limit/offset/first_timestamp/last_timestamp |
| DELETE /buildings/{id}/measurements/{measurement_id} | Empty204; hard delete after UI confirmation |
| POST /buildings/{id}/measurements/import | 200, committed import summary |

GET uses descending timestamp then descending id, default100, maximum500, positive limit and nonnegative bounded offset. Count/min/max are calculated in SQL for the whole building, not just the page; empty history returns zero and null endpoints. Existing building_id/timestamp/unique indexes are retained. Offset pagination is not a snapshot while concurrent writes occur. No single-record GET or historical edit endpoint is added.

## Manual entry and history

Open an owned building, choose Add measurement, and provide local timestamp plus all fields in Energy, Indoor conditions and Outdoor/weather groups. No defaults are supplied. Successful storage refreshes history/count; refresh and backend restart retain records. History shows a concise subset with units, all-fields disclosure, pagination, and confirmed deletion. Loading/error/retry/empty states are explicit. The shared QueryClient uses account/building/page keys and invalidates all pages only after server-confirmed mutations; logout clears private caches. Session verification failures remain guarded.

## CSV format and atomicity

Upload UTF-8 (optional BOM), comma-separated CSV with an exact case-sensitive header. Supply exactly one `date` or `timestamp` column and all 26 numeric fields. Column order is arbitrary. No arbitrary mappings, engineered columns, duplicate headers or both date aliases are accepted. Optional rv1/rv2 are explicitly ignored, reported in ignored_columns, never validated as predictors and never persisted. Other extra columns are rejected. Header-only CSV is invalid; the downloadable template intentionally contains just a header, to be completed with actual observations:

```csv
timestamp,Appliances,lights,T1,RH_1,T2,RH_2,T3,RH_3,T4,RH_4,T5,RH_5,T6,RH_6,T7,RH_7,T8,RH_8,T9,RH_9,T_out,Press_mm_hg,RH_out,Windspeed,Visibility,Tdewpoint
```

CSV numeric text is converted to finite floats. Missing/extra cells, malformed dates, malformed quoting, non-finite values, duplicates within the file and unsupported headers reject the whole import with422. Row errors include one-based CSV record number (header is1), field and safe message; for quoted multiline fields this is a record number, not physical line number. Existing database timestamp conflicts return409. No rows are skipped or silently replaced.

Files are read with a 16MiB limit and limited to25,000 rows, enough for the verified19,735-row UCI source. FastAPI UploadFile may spool multipart content to an OS temporary file before application validation; uploads are closed, and no permanent repository copy is written. This is a local prototype, not an ingress-level streaming quota. Deployments need web-server request limits and authentication rate limits.

Every row is validated before database writes. Existing timestamps are checked in batches; inserts use SQLAlchemy bulk batches of500 within one transaction, committed once. The database uniqueness constraint handles races. Integrity failures roll back earlier batches; unexpected database failures also roll back through session lifecycle. No per-row commits, background jobs, dataset mutation, preprocessing or model loading occur. Import result includes building_id, rows_received, rows_imported, first_timestamp, last_timestamp and ignored_columns. The UI reports success only after commit, and shows safe errors otherwise. FormData uses browser-generated multipart boundaries and a120-second upload timeout; if a response is lost after commit, retry may report409, so inspect history before retrying.

## Explicit UCI reference import

First install dependencies and migrate using the established workflow. Select an existing active ADMIN (bootstrap explicitly with `python scripts/create_admin.py` if needed). Then run:

```powershell
python -m pip install -r requirements.txt
python -m alembic upgrade head
python scripts/import_uci_reference_building.py --admin-email administrator@example.com
```

The command reads only the existing local `data/raw/energydata_complete.csv`; it never downloads or rewrites it. It uses the configured DATABASE_URL and creates **UCI Reference Building** under the selected ADMIN, with exact provenance description: the model was developed/validated on this reference research data, which is not live operational telemetry. It invents no city, address, area or building type, never promotes accounts, never runs at startup, and never attaches the data to new users. The current owner-only policy keeps the reference private to its ADMIN.

No is_reference column/migration is needed. The local utility identifies an owner's reserved name plus exact provenance description. A name collision, multiple matching names, or existing reference history rejects without changes; an exact empty reference may be populated. This is an explicit serial local utility: do not run simultaneous reference importers, because reference-name uniqueness is not a database constraint. Normal CRUD metadata can be edited; renaming a reference removes its utility identity, and the script is not a general provenance registry. No public-reference access or protected administrative building API is added.

## Reproduce verification

```powershell
python -m pytest -q
node --experimental-strip-types --test tests/frontend_api.test.mjs tests/frontend_auth.test.mjs tests/frontend_buildings.test.mjs tests/frontend_measurements.test.mjs
node node_modules/typescript/bin/tsc --noEmit
npm run build
python tests/verify_uci_reference_import.py
python tests/verify_measurements_browser.py
```

The full-import verifier uses a disposable migrated SQLite DB, runtime ADMIN credentials and the real CLI. It compares every value/timestamp to the source, verifies count, absence of rv1/rv2/duplicates/predictions, safe repeat rejection and unchanged source checksum. The browser verifier extends the full authentication/building regression, exercises manual entry and actual FormData uploads, invalid-file atomicity, duplicates, deletion/cancel, refresh/restart persistence, cross-owner API/UI isolation and responsive history. All accounts, profiles, DBs and own processes are temporary and cleaned; generated logs/evidence/screenshots remain ignored. No developer DB is used. The only new dependency is python-multipart for FastAPI UploadFile; frontend dependencies/lockfiles/migrations remain unchanged.

Known limitations: no editing/bulk deletion, no background imports or progress streaming, bounded synchronous local import, naive local times, offset-page concurrency and reserved-name reference identity. No automatic feature construction, prediction/readiness service, persisted forecasts/recommendations, admin panel or IoT integration. These remain later-phase work. Phase 24 audit: [phase24_measurements_import.json](../ml/results/phase24_measurements_import.json).
