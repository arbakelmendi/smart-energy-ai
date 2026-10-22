# Automatic feature construction and prediction readiness (Phase 25)

Stored raw measurements now support a backend-only, deterministic compatibility assessment and an internal latest inference row. This phase does not run XGBoost, execute recommendations, create Prediction records, or persist engineered features. The existing public research APIs retain their historical behavior.

## Authoritative contract and shared calculations

[feature_schema.json](../ml/results/feature_schema.json) supplies the exact ordered 42 model columns, verified against [final metadata](../ml/results/final_model_metadata.json), including its schema SHA256. The builder has no competing hardcoded feature list and does not infer order from dictionaries. Raw fields come from the existing Measurement contract: timestamp plus the 26 exact numeric columns, including current Appliances and excluding rv1/rv2. Building name/type/city/area/owner never become model inputs. Units and naive-local measurement semantics remain as documented in [measurement import](measurement-import.md).

`engineer_origin_features` was extracted without changing any formula from [feature_engineering.py](../ml/src/feature_engineering.py). Both the supervised research workflow and the new application service call it. It copies the validated chronological raw frame and constructs origin-time features without labels, row removal or file IO:

| Features | Exact semantics |
| --- | --- |
| hour, day_of_week, month, is_weekend | Origin timestamp; integer hour 0-23, weekday Monday 0-Sunday 6, month 1-12, weekend weekday>=5 |
| hour_sin / hour_cos | sin/cos(2*pi*integer_hour/24); minutes do not become fractional hours |
| dow_sin / dow_cos | sin/cos(2*pi*weekday/7) |
| appliances_lag_1 / 6 / 144 / 1008 | Appliances at t-1, t-6, t-144, t-1008 intervals relative to forecast origin, not target |
| appliances_roll_mean_1h / std_1h | Last 6 observations including t, backward uncentered, min_periods=6, sample std ddof=1 |
| appliances_roll_mean_24h / std_24h | Last 144 observations including t, backward uncentered, min_periods=144, sample std ddof=1 |

The pure builder selects columns with an explicit schema-ordered list and returns a frozen LatestFeatureRow: feature_timestamp, feature_names tuple and values tuple. `as_frame()` creates exactly one finite numeric row with those explicit columns, directly accepted by the existing production feature validator without repair/reordering. No model artifact is opened by readiness. Missing/malformed contract metadata gives a safe 503 rather than an invented readiness response.

## Minimum history and latest-window policy

The exact minimum comes from the finalized constants, not row-count guesswork:

`required_history_intervals = max(max(LAG_STEPS), max(ROLLING_WINDOWS.values())-1) = 1008`

`required_observations = required_history_intervals + 1 = 1009`

That means the current observation plus 1008 earlier observations at exact ten-minute adjacent intervals. A 1008-row history is insufficient even when gap-free. Uniqueness alone does not prove continuity. Readiness requires finite complete raw data and a fully finite 42-feature output, not only a timestamp check.

The database service reads a SQL total count and at most 1010 newest rows, ordered by timestamp descending then id descending; it reverses them to chronological order. The extra row guards duplicate corruption exactly at the retained-window boundary. Pure assessment also sorts timestamped input defensively, independently of insertion IDs. It validates only the latest 1009 observation values and exact 600-second spacings inside that required window. Older gaps and older invalid raw values outside it do not block a valid latest window. The boundary's preceding interval is not required; an equal boundary timestamp is rejected as ambiguity. The entire building lifetime is never loaded for an interactive readiness request.

A recent gap, including irregular intervals shorter than ten minutes, returns not-ready. The gap response reports the nearest incompatible adjacent interval when scanning back from the latest measurement; `first_gap` means first encountered in that backward assessment, not the earliest lifetime gap. `continuous_intervals_available` counts the latest exact ten-minute suffix, capped at 1008. A zero-row or single-row history has zero continuous intervals. This is data availability, not a readiness percentage. Invalid raw values may coexist with a long timestamp-contiguous suffix, so they still block readiness.

Deleting an interior required observation breaks readiness. Restoring it can restore readiness. A new latest measurement always becomes the candidate origin; a 20-minute gap must fail even if an older origin was ready. There is no fallback to an older timestamp. Old missing history that has moved outside the required window does not matter. Storage still permits arbitrary timestamps; readiness does not silently resample, interpolate, fill, round timestamps to a grid, or synthesize observations. Exact ten-minute spacing is checked without requiring an absolute clock-minute grid.

## Inference versus supervised targets

At latest observation t, current Appliances_t is a valid known predictor. The model's future target is Appliances_(t+10minutes), in Wh. Its value is neither an input nor a readiness requirement. The historical supervised workflow alone adds target_appliances_next via shift(-1), then drops the final row because its label is unknown. Inference does not make that final-row exclusion: the current final raw row can be used to construct a complete input even without a future observation. No target or forecast value is generated here.

## Architecture and endpoint

[backend/prediction_features.py](../backend/prediction_features.py) separates:

- `get_latest_required_history`: bounded database retrieval. An internal as_of cutoff exists solely for deterministic historical verification; there is no API cutoff parameter.
- `assess_history`: pure dictionary-observation validation, latest-window assessment and shared transformation.
- `build_latest_feature_row`: pure convenience wrapper returning the feature row or structured HistoryNotReady.
- `assess_prediction_readiness`: count/fetch/assessment service returning readiness and optional internal feature row.

The only new route is authenticated `GET /buildings/{building_id}/prediction-readiness`. Existing USER and ADMIN owner-only policy applies; non-owned and missing buildings have the same 404. All building responses remain no-store. No schema/migration, new dependency, feature-preview endpoint, forecast route or database feature table is added.

Response fields: building_id, ready, latest_measurement_timestamp, measurement_count, required_history_intervals, required_observations, continuous_intervals_available, required_interval_minutes, reason_code, message and nullable first_gap (before_timestamp, after_timestamp, actual_interval_seconds). Measurement times retain timezone-naive local semantics. No features or prediction values are exposed.

| Reason code | Meaning |
| --- | --- |
| NO_MEASUREMENTS | No stored observations |
| INSUFFICIENT_HISTORY | Latest available observations have no detected spacing break but fewer than1009 exist |
| LATEST_WINDOW_HAS_GAPS | At least one required adjacent interval differs from ten minutes; this can take precedence over insufficient count after deletion |
| INVALID_RAW_DATA | Ambiguous/invalid timestamps, missing/non-numeric/non-finite raw values, or non-finite/inconstructible feature row |
| READY | Exact latest-window compatibility and a finite complete 42-feature row verified; no forecast executed |

A metadata contract failure is 503. Corrupt local SQLite timestamp decoding fails safely as INVALID_RAW_DATA, without disclosing the corrupted value or a traceback. The pure service rejects duplicates even though the normal measurement table already prevents them. No missing values are filled with zeros, means, medians or neighboring observations.

## Frontend behavior

Existing building detail shows Prediction readiness with an understandable backend-derived state, stored count, latest timestamp, required observations/spacing, capped contiguous suffix and gap endpoints. It has real loading/error/retry states, no fallback and no percentage. It clearly distinguishes input compatibility from forecast execution and model validity for a new building; a compatible history is not evidence of model transfer accuracy.

The typed native client validates the response and includes session credentials. The existing QueryClient partitions readiness keys by account and building. Successful manual create, CSV import and measurement delete invalidate both all history pages and that readiness query. There is no optimistic ready state and no frontend lag/rolling/cyclical computation. Logout retains private-cache cleanup, and 401 triggers session revalidation. Normal concurrent mutations can change readiness immediately after a read; this is not a reservation/snapshot for a later forecast. Phase 26 must reassess at execution.

## UCI parity and research regression

The real Phase 24 reference utility imports 19,735 source rows into a disposable migrated DB, with an explicit private ADMIN owner. Verified first inference-ready timestamp: **2016-01-18T17:00:00** (raw row index 1008). Three 42-feature comparisons use TRAIN/VALIDATION origin timestamps:

| Origin timestamp (naive local) | Maximum absolute feature difference |
| --- | --- |
| 2016-01-18T17:00:00 | 7.105427357601002e-15 |
| 2016-02-29T09:00:00 | 1.4495071809506044e-12 |
| 2016-05-01T21:00:00 | 1.0800249583553523e-12 |

All 126 compared values pass absolute tolerance 1e-10, relative tolerance 0. Exact columns and discrete/current/lag values are checked; tiny raw parser and rolling-standard-deviation roundoff comes from float64 CSV parsing/serialization and initializing a bounded rolling prefix rather than the entire lifetime. The formulas are identical, with no approximated window or altered statistics. The tolerance is an absolute numeric reproducibility bound, not a statistical confidence interval.

The unchanged supervised workflow's complete CSV export is reproduced only in an OS temporary directory and is byte-for-byte equal to the historical feature artifact (SHA256 f69480c282e32601920f0820cdf9d2530ecfc5b053c4cefa4de2d15c73c2077f). Original leakage/alignment checks pass. No historical artifacts are overwritten. The full reference's last raw observation 2016-05-27T18:00:00 is also ready without a next target; this is a deterministic latest-history check, not a new held-out evaluation or model-selection use. No fitting, inference, metrics, threshold or recommendation calculation changes.

## Reproduce checks

Use the established migrated application environment and existing local datasets/artifacts. No additional dependency is required.

```powershell
python -m pytest -q
node --experimental-strip-types --test tests/frontend_api.test.mjs tests/frontend_auth.test.mjs tests/frontend_buildings.test.mjs tests/frontend_measurements.test.mjs tests/frontend_readiness.test.mjs
node node_modules/typescript/bin/tsc --noEmit
npm run build
python tests/verify_feature_parity.py
python tests/verify_readiness_browser.py
```

The parity script verifies source hashes, full research export identity, all 42 values at multiple historical prefixes, latest target-free inference construction and zero Prediction rows. Unit tests independently verify formulas, minimum history, ordering, leakage/gaps/corruption and owner/session isolation. Live browser QA includes the full authentication/building/CSV regression plus empty -> insufficient -> ready -> delete/gap -> restore/ready, a new-latest gap, automatic create/import/delete invalidation without page refresh, second-user and ADMIN policy, full reference readiness and responsive UI. All QA uses disposable DBs/accounts/profiles and cleans its own processes. Generated logs/evidence/screenshots remain ignored. Existing public research forecast/helper equivalence is tested separately as regression; readiness never calls those routes or helpers.

Known limitations: naive local timestamps retain timezone/DST ambiguity, checks do not establish sensor quality/physical plausibility or cross-building model validity, and there is no concurrent-read snapshot guarantee across count/history statements. Counts use SQL aggregation while feature retrieval stays bounded. Numeric parity has the documented float64 tolerance; schemas/dependencies remain the existing finalized contract. No building forecast, persisted prediction/recommendation, feature table, admin panel or automatic ingestion is implemented. Phase 26 is not started. Audit: [phase25_feature_construction_readiness.json](../ml/results/phase25_feature_construction_readiness.json).
