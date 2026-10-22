# Building forecasts and persisted recommendations (Phase 26)

An authenticated owner can explicitly predict Appliances energy for the next ten-minute interval from stored building history. This extends the application pathway; it does not retrain/tune/select a model, alter research artifacts or thresholds, redesign dashboards, schedule forecasts, or control equipment.

## Flow and authoritative sources

`POST /buildings/{building_id}/predictions` accepts no body (or an empty object). Nonempty bodies, including caller-provided features/source/model/owner fields, are rejected. The existing active session and mutation CSRF/trusted-origin guard apply. USER and ADMIN both need ownership; missing and non-owned buildings receive uniform 404.

The thin route calls [building_prediction_service.py](../backend/building_prediction_service.py), which:

1. Reassesses current database history through Phase 25 [prediction_features.py](../backend/prediction_features.py). It requires the current plus 1008 preceding observations at exact ten-minute intervals and obtains the exact 42 ordered production features. Frontend readiness is never trusted.
2. Reuses `backend.services.model_bundle()`, the existing cached and checksum-verified loader for `ml/models/final_xgboost_model.json`. The finalized [model_inference.py](../ml/src/model_inference.py) path is retained; no parallel XGBoost constructor/loading path exists.
3. Fingerprints the precise feature row and checks for an existing persisted result with the same input identity.
4. For a new identity, calls the same integrated Phase 14 `predict_and_recommend` helper used by the generic research recommendation API, with the existing cached model bundle and threshold resource. This delegates to production inference and the authoritative recommendation rules; no duplicated threshold classification or calibration occurs.
5. Validates finite output and the existing recommendation response. It rechecks history after inference and rejects intervening input changes.
6. Flushes and validates the new forecast plus recommendation/input snapshot, then commits once. Only a confirmed commit returns success. Integrity races reuse the winning record; other persistence failures roll back and return safe 503.

Expected not-ready conditions return 409 with structured readiness details, not 500, without loading the model or inserting a Prediction. A change detected during inference returns 409 HISTORY_CHANGED (or the newly detected readiness failure). This closes important stale-client/intervening-change cases but does not promise a serializable reservation across all concurrent requests: an observation can still change after the last check. The persisted feature snapshot describes what the model actually consumed, and history labels are reassessed on read.

## Semantics and domain

For latest source observation t, the output is Appliances energy in **Wh** for the next ten-minute interval, with forecast timestamp **t + 10 minutes**. Measurement/source/forecast timestamps preserve Phase24 naive building-local semantics; created_at is naive UTC audit time. It is energy, not instantaneous power, accuracy, measured future consumption or confidence. Current Appliances_t is a valid known input; no future target is required. No forecast is clipped.

The existing recommendation engine requires nonnegative current energy and rejects negative forecasts. Phase26 adds no new arbitrary bounds: a negative current input gives a deliberate 422 for that existing policy, and an invalid/non-finite/negative model result or recommendation failure gives controlled 503 without persistence. Raw general measurement storage remains as previously defined.

The model was validated on the UCI reference building. Predictions for other buildings are **experimental**, even with compatible history. This notice is included in API responses and shown on every building forecast panel. The explicitly imported UCI Reference Building already carries its source/provenance description and ADMIN ownership; matching a name alone never proves external validation. Technically compatible other buildings are permitted; no inferred occupancy, comfort, intervention benefit or cross-building accuracy is claimed.

Recommendations are decision support. The new pathway calculates no savings, confidence, CO2, costs, percentage improvement or automatic control action. It does not persist trend; current measured energy for a saved forecast is recovered from its immutable input snapshot, so the UI labels it **Measured Appliances at forecast source**, not necessarily the building's latest current reading.

## Persistence and migration

The existing Prediction table stores building_id, source_timestamp, prediction_wh, horizon_minutes=10, verified model_name and exact model SHA256, recommendation_level/code/priority/text and created_at. The four recommendation fields are copied from the actual integrated helper: prediction.level, recommendation.code, recommendation.priority and recommendation.message. The recommendation title/rationale/threshold map are not re-created on history reads or silently reclassified.

A justified new migration, **0026_prediction_feature_snapshots**, follows 0022_authentication_sessions without editing previous migrations. Run before using the new routes:

```powershell
python -m alembic upgrade head
```

It adds nullable `feature_hash` and `feature_snapshot_json`, a paired-presence/hash-length check and unique `(building_id, source_timestamp, model_checksum, feature_hash)`. New application predictions always contain both fields. Legacy rows are preserved with null snapshot/hash; their measured source value and current-input match cannot be invented. History shows them as historical and handles missing recommendation snapshots explicitly. The old PredictionData foundation DTO remains unchanged; dedicated response DTOs cover the application API.

The snapshot JSON contains only ordered feature_names and feature_values. `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)` defines canonical bytes, and SHA256 of UTF-8 bytes defines feature_hash. Exact float64 values are retained in the per-prediction snapshot; no new engineered-feature table exists. No emails, credentials, session tokens or other user metadata enter the snapshot.

The same building/source/model/fingerprint reuses its persisted record and reports reused_existing_prediction=true. A compatible new latest source creates a new record. An irrelevant older insert or restoration of identical model inputs reuses the original result. A historical correction affecting lag/rolling/current inputs changes the fingerprint and creates a new version for the same source, preserving previous records. Changes to raw history that do not change any consumed feature intentionally do not create a new identity. No measurement mutation automatically predicts or deletes history.

Database uniqueness handles concurrent identical requests: inference work can occur twice, but only one record persists; a unique conflict retrieves the winner. SQLite contention or other failures can return 503, and retry remains idempotent. A lost response after commit may also leave a client uncertain; inspect history/retry instead of assuming no write. No background scheduler, request queue or global mutable model state is introduced. Existing model/threshold caches last for the process lifetime; restart after deliberate artifact/configuration changes. A missing artifact fails safely when loading uncached resources; an already verified in-memory model continues under the existing cache behavior. No dummy model is substituted.

Upgrade/downgrade/reupgrade tests preserve legacy scalar predictions. Downgrade deliberately removes the new audit columns and constraint and therefore their snapshot context; it does not invent or deduplicate records. Production use should retain the new migration. No dependencies/lockfiles are changed.

## History API and current versus historical

`GET /buildings/{building_id}/predictions?limit=50&offset=0` is owner-only and no-store, default 50, maximum 500, nonnegative bounded offset. It returns items/total/limit/offset plus current_source_timestamp/current_history_ready. Rows are ordered created_at descending then id descending. There is no unnecessary single/latest endpoint; the first page supplies the latest stored result.

Each item includes IDs, source/forecast timestamps, prediction_wh, unit Wh, horizon, model name/checksum, nullable feature hash/source measured value/recommendation, created_at, validation notice and `matches_current_history`. The POST response adds reused_existing_prediction. Technical input snapshots are retained internally, not sent as 42-feature browser payloads.

History never loads the model or executes predictions/recommendations. It uses current Phase 25 compatibility and metadata-only model identity to assess whether each snapshot still matches current source, fingerprint and checksum. If compatibility/metadata cannot be established, matches_current_history is false while readable historical rows remain available. The API compares fingerprints even when a historical correction leaves source timestamp unchanged. A corrupt non-null snapshot fails safely rather than fabricating a measured value.

The frontend uses the existing credentialed native client and QueryClient with account/building/page keys. POST includes CSRF and no feature body. Success invalidates all pages for that owner's building. Measurement create/import/delete invalidate history/current-match context as well as measurements/readiness. No optimistic prediction or cross-building cache invalidation occurs. Expired 401 revalidates the session; 409 revalidates readiness.

The existing building detail now has an explicit **Predict next 10 minutes** action, disabled while readiness is unavailable/not-ready/rechecking. Page loads only read readiness/history; model execution needs the user's click. The result shows predicted Wh (three decimal places for display; full precision remains stored/API), horizon, source/forecast timestamps, source measured energy and recommendation. It labels a prior result as historical when current-input matching is false or being rechecked. A later history page is labeled a stored snapshot, not the globally latest result. History has real empty/loading/error/retry states, pagination and newest-first persisted rows. There is no apply/control button or manufactured confidence/savings.

## Research API distinction and parity

The existing generic public `POST /forecast` and `POST /forecast/recommendation` remain unchanged: technical callers provide 42 already-engineered features. The owned building route constructs them on the server, reassesses current stored history and persists/reuses the result.

In an isolated database, TRAIN origin 2016-01-18T17:00:00 produces 55.505409240722656 Wh, identical to the direct production helper (difference 0.0 Wh); its saved recommendation fields exactly match the integrated Phase 14 helper. The full 19,735-row UCI reference import is ready at 2016-05-27T18:00:00 and produces 339.7279052734375 Wh for 18:10, again difference 0.0 Wh with exact recommendation parity. These are reproducibility checks of the finalized model, not new validation metrics, retuning or evidence of transfer accuracy. Repeat reference requests return the same record and one history row.

## Reproduce verification

Use the existing virtual environment, ignored local final model and source datasets described in the reproduction guide. After migration, use the established FastAPI/frontend startup commands. No new dependency is needed.

```powershell
python -m pytest -q
node --experimental-strip-types --test tests/frontend_api.test.mjs tests/frontend_auth.test.mjs tests/frontend_buildings.test.mjs tests/frontend_measurements.test.mjs tests/frontend_readiness.test.mjs tests/frontend_predictions.test.mjs
node node_modules/typescript/bin/tsc --noEmit
npm run build
python tests/verify_building_predictions.py
python tests/verify_predictions_browser.py
```

Backend tests cover true helper equivalence, persistence, ownership, CSRF, not-ready/stale readiness, idempotency, concurrent uniqueness, new/latest and historical edits, missing resources, non-finite/negative output, inference/recommendation failures, DB rollback, pagination, safe legacy records and migration preservation. Native frontend tests cover request/response/error contracts and private invalidation. Browser QA extends all prior auth/building/measurement/readiness checks with insufficient-history gating, explicit prediction, persisted recommendation, refresh/backend restart, idempotent repeat, new compatible measurement/new history record, old-result labeling, owner isolation, full reference UI and responsive layouts. All accounts/DBs/profiles/processes are isolated and cleaned. Evidence/screenshots/logs stay ignored.

Known limits: naive-local timezone/DST ambiguity; no reservation against all concurrent history edits; model/threshold resources cached until restart; offset pagination can shift under writes; legacy records lack new input provenance; fingerprint depends on the exact feature numeric values and current serialization/runtime (tiny floating differences after a future runtime change can intentionally create a new identity). Fixed Phase 14 rules are not fingerprint-versioned separately because thresholds are unchanged in this phase. None of these checks establishes new-building validation or measured intervention savings. No Phase 27 dashboard redesign, scheduler, admin management, IoT or automatic actuation is implemented. Audit: [phase26_building_predictions.json](../ml/results/phase26_building_predictions.json).
