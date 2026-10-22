# User building dashboard (Phase 27)

## Start and use

Use the existing installation and localhost server commands in [reproducibility](reproducibility.md), initialize the database with `python -m alembic upgrade head`, and sign in. No new dependency, migration, administrator setup or background worker is required by this phase.

1. Open `/dashboard`. A new account sees **No buildings yet** and a building-management link.
2. Create an owned building at `/buildings`; **Open building dashboard** preserves its ID in `/dashboard?building=123`.
3. Manage measurements through the existing building detail page. See [measurement import](measurement-import.md) for required fields, units and atomic CSV validation.
4. Return to the dashboard to inspect actual counts, latest raw measurement, bounded observed energy history and backend readiness.
5. Once ready, explicitly request a forecast. The dashboard displays the persisted matching forecast and recommendation. No prediction runs automatically.
6. Follow prediction history or saved recommendations for that selected building. These are persisted snapshots, not active alerts or measured interventions.

## Selection and privacy

The selector lists the authenticated user's buildings. With no query parameter, it selects the first returned owned building. An explicit invalid, deleted or foreign ID produces **Building unavailable**; it never silently chooses another building or fetches that foreign building's dashboard. Backend ownership is independently enforced for USER and ADMIN, with uniform404 for non-owned/missing IDs.

The URL carries selection across refresh and links. Queries are partitioned by authenticated user, building and chart window; selection changes remount local building state. Logout clears private cache; account changes use separate user keys. Confirmed measurement changes invalidate history, readiness, predictions and dashboard windows. Forecast creation refreshes summary/history; building edits refresh metadata. Deletion cancels and removes cached child queries. These are ordinary request-driven queries, not live sensor subscriptions or a scheduler.

Private responses retain `Cache-Control: no-store`. Backend error and malformed-response states hide operational values and offer Retry rather than substituting fixtures. During refresh, an old forecast is not asserted to be current.

## Read-only summary API

`GET /buildings/{building_id}/dashboard-summary?limit=144` requires an active owner session. Limit is 1-500; default144. It returns building metadata; measurement count and earliest/latest timestamps; nullable latest raw measurement; shared Phase25 readiness; prediction count; nullable current and latest stored predictions; latest five persisted predictions; and a bounded ascending observed Appliances history.

The endpoint checks ownership first. Counts use SQL aggregates; chart rows are limited in SQL. Readiness fetches the same bounded latest history used by Phase25. The shared Phase26 prediction context calculates the latest feature fingerprint and reads saved model metadata without loading/executing a model or recommendation engine. The exact matching persisted prediction is looked up by identity independently of the latest-five preview. Restoring earlier inputs can therefore recover their matching snapshot even after many subsequent versions. Nothing is written by summary requests.

See [building predictions](building-predictions.md) for identity, idempotency, snapshots and the existing explicit POST API. A forecast is current only if source timestamp, exact current feature fingerprint and recorded model checksum match the shared context, with history still ready. Appending an observation or changing relevant history makes the previous result historical; its recommendation is not shown as current. Forecast age alone does not establish freshness. An unavailable feature contract returns a safe503.

## Measurements and chart semantics

All dashboard values come from stored building observations and backend responses. Genuine zero Wh remains zero. The chart selects the latest144 or500 **stored observations**, not a promised day or week. It orders actual local timestamps chronologically and plots individual points against elapsed wall-clock coordinates. Missing intervals remain visible as gaps: there is no resampling, invented point, connected interpolation, smoothing or frontend feature construction.

Measurement/source/target timestamps retain the existing timezone-naive building-local policy. The chart uses a UTC-based numeric coordinate only to preserve wall-clock spacing and stable labels across browser timezones; this does not assign UTC to a measurement or convert its meaning. Original timestamp strings appear in tooltips. Prediction creation timestamps are separately labeled UTC. Daylight-saving ambiguity cannot be resolved without reliable source timezone metadata; the existing naive validation policy still applies.

Readiness displays authoritative states and continuity evidence, not a client-side count threshold. The required1009 consecutive ten-minute observations and42 feature formulas remain unchanged. Building metadata is context, not an additional model feature. No occupancy, equipment attribution, live feed, automatic control, savings or confidence intervals are inferred.

## Research and operational boundaries

The expandable **Model / Research Information** section retains the existing API-driven test metrics, validation comparison, predictive importance and recommendation bands. Those results describe the original UCI research experiment, not the selected building. The section mounts on demand. Non-reference-building forecasts remain experimental and do not establish external validation, physical control or measured savings.

`/predictions?building=123` and `/recommendations?building=123` provide paginated owner-scoped ledgers with source/target times and current-history labels. `/data` now explains actual measurement management instead of mock reports/downloads. Admin functionality is unchanged; Phase28 is not implemented.

## Verification

Run from the repository root with existing dependencies:

```powershell
.venv\Scripts\python.exe -m pytest -q
node --experimental-strip-types --test tests/frontend_*.test.mjs
node node_modules/typescript/bin/tsc --noEmit
npm run build
.venv\Scripts\python.exe tests/verify_user_dashboard_browser.py
```

The browser verifier requires installed Edge, `websocket-client`, available dynamic localhost ports and the existing local UCI source. It creates a temporary migrated database, uses real development-source observations for verification, exercises prior authentication/building/measurement/readiness/prediction flows plus dashboard selection, stale/current transitions, persistence, malformed-response Retry and account isolation, and checks desktop/mobile rendering. It stops only its own processes and removes its temporary DB/browser profile. Evidence and screenshots are ignored under `ml/results/generated`; they are not application data or new research results. The phase audit is [phase27_user_dashboard.json](../ml/results/phase27_user_dashboard.json).
