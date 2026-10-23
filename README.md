# SmartEnergyAI

**Artificial Intelligence for Prediction and Optimization of Energy Consumption in Smart Buildings**

SmartEnergyAI is a full-stack Bachelor-thesis research/application prototype for **10-minute-ahead Appliances energy prediction in Wh** and transparent **forecast-based decision support**. It combines a reproducible Python workflow, a persisted Tuned XGBoost model, FastAPI, and the existing React/TypeScript TanStack Start dashboard.

The objective is to compare forecasting approaches chronologically, estimate later-period performance and turn forecasts into conservative review recommendations. Optimization means decision support here, not automatic building control or validated intervention savings.

## Implemented capability and scope

- Predict `target_appliances_next`: information available at or before t predicts `Appliances` at t+1, ten minutes later. Current `Appliances_t` is a known input.
- Separate validation model comparison from the selected final model's held-out test performance.
- Explain predictive behavior with saved gain and permutation importance.
- Return deterministic recommendations calibrated on TRAIN + VALIDATION only.
- Present API-sourced research results with explicit loading/error/unavailable states.

USER accounts manage owned buildings, persist manual/CSV measurements, check continuity-based readiness, explicitly generate building forecasts/recommendations and inspect real dashboards/history. ADMIN has dedicated cross-owner overview, user/building/activity inspection and guarded deactivation/reactivation. Passwords, sessions and operational data persist in the relational database. Research evidence remains separately labeled.

There is no live IoT stream, automatic forecasting scheduler, occupancy inference, equipment control, verified intervention savings or calibrated prediction interval. Predictions for user-created buildings are experimental; the model was validated on one UCI reference building. [Final overview](docs/final-application-overview.md) is the evaluator entry point.

## Dataset and methodology

The [UCI Appliances Energy Prediction dataset](https://doi.org/10.24432/C5VC8G), DOI **10.24432/C5VC8G**, has **19,735 rows and 29 columns** in the recorded raw inspection. Coverage is **2016-01-11 17:00:00 through 2016-05-27 18:00:00**, at an exact ten-minute interval. Recorded checks found no missing values, duplicate rows or duplicate timestamps. `Appliances` and `lights` measure energy in Wh; Wh is not instantaneous power.

The data covers one building during January-May, without a reliable occupancy observation for this model. Preprocessing removes only the identical random/questionable `rv1`/`rv2` columns; rows and target outliers are retained. See [provenance](data/raw/README.md) and [methodology](docs/research-methodology.md).

There are **42 engineered features**: current physical/environmental readings, temporal fields, cyclical encodings, historical consumption lags and backward-looking rolling statistics. Lags are relative to forecast origin: 1/6/144/1008 ten-minute steps correspond to 10 minutes/1 hour/24 hours/7 days. Rolling windows end at the origin, including current and past readings only.

Nominal chronological partitions are 70% TRAIN / 15% VALIDATION / 15% TEST, without shuffling. Exact boundaries for the 18,726 supervised samples come from [split metadata](ml/results/split_metadata.json):

| Split | Rows | First forecast origin | Last forecast origin |
| --- | ---: | --- | --- |
| TRAIN | 13108 | 2016-01-18 17:00:00 | 2016-04-18 17:30:00 |
| VALIDATION | 2809 | 2016-04-18 17:40:00 | 2016-05-08 05:40:00 |
| TEST | 2809 | 2016-05-08 05:50:00 | 2016-05-27 17:50:00 |

TRAIN fits parameters and training-only preprocessing. TRAIN-only expanding time-series CV supports tuning; VALIDATION supports comparison and selection. TEST is excluded from development/selection. The locked final configuration is fitted on TRAIN + VALIDATION (15,917 rows) before final held-out evaluation. Timestamps above are forecast origins; target-time alignment is explained in the methodology guide.

## Validation comparison and final model

These are **VALIDATION metrics**, from [Phase 10](ml/results/phase10_tuning_summary.json), incorporating saved [baseline](ml/results/phase7_validation_metrics.json), [Random Forest](ml/results/phase8_random_forest_validation_metrics.json) and [XGBoost](ml/results/phase9_xgboost_validation_metrics.json) results:

| Model | Validation MAE (Wh) | Validation RMSE (Wh) | Validation R-squared |
| --- | ---: | ---: | ---: |
| Persistence Baseline | 25.920256318974722 | 65.79497157144202 | 0.46527285610821445 |
| Linear Regression | 27.02529387063962 | 59.346237268480074 | 0.5649559830358953 |
| Untuned Random Forest | 53.004521181915266 | 100.81836183251377 | -0.25552711394804195 |
| Tuned Random Forest | 33.03036877970391 | 64.50352076663437 | 0.4860585286448823 |
| Untuned XGBoost | 54.392578125 | 90.57733660386576 | -0.013411760330200195 |
| Tuned XGBoost | 25.493202209472656 | 57.62563762187907 | 0.5898163318634033 |

**Tuned XGBoost** was selected by lowest validation RMSE: **57.62563762187907 Wh**. The [selection lock](ml/results/phase11_selection_lock.json) records the exact parameters, feature order and tie rule. The [methodology guide](docs/research-methodology.md) includes the complete locked configuration. Other candidates were not evaluated on the final test set.

### Final held-out TEST results

Only the selected final model has these [Phase 11 results](ml/results/phase11_final_test_evaluation.json):

| Held-out TEST metric | Exact Phase 11 value |
| --- | ---: |
| MAE (Wh) | 25.891124725341797 |
| RMSE (Wh) | 59.11701146812037 |
| R-squared (dimensionless) | 0.5820133686065674 |

No post-test tuning occurred. R-squared is dimensionless, not percentage accuracy. The estimate describes one later chronological period from the same building.

## Explainability and recommendations

[Phase 12](ml/results/phase12_feature_importance.json) records normalized gain and held-out permutation diagnostics. Current/historical consumption strongly informs the model; method rankings differ. **Predictive importance is not causality, physical energy contribution or achievable savings.** The dashboard shows saved top-ten gain fractions.

Thresholds use 15,917 TRAIN + VALIDATION targets only: p50=60, p75=100, p90=190, p95=320 Wh, with linear interpolation. TEST and the whole-dataset EDA threshold are excluded. [Phase 14 metadata](ml/results/phase14_recommendation_thresholds.json) defines:

| Level | Forecast band (Wh, next 10 minutes) | Stable code |
| --- | --- | --- |
| NORMAL | prediction < 100 | NORMAL_CONSUMPTION |
| ELEVATED | 100 <= prediction < 190 | ELEVATED_CONSUMPTION |
| HIGH | 190 <= prediction < 320 | HIGH_CONSUMPTION |
| VERY HIGH | prediction >= 320 | VERY_HIGH_CONSUMPTION |

Rules conservatively suggest reviewing flexible/non-essential loads where safe. They do not control equipment or estimate savings. Trend is forecast minus current Wh; percentage change is undefined at zero current energy. See [model/inference usage](ml/models/README.md).

## Architecture and repository

The research path is dataset -> preprocessing -> origin-time features -> chronological splits -> fitting/CV/validation -> locked final model -> held-out evaluation -> native persistence. The serving path is typed frontend -> FastAPI -> shared inference/recommendation helpers. Read-only research endpoints expose committed results. See the [architecture diagram](docs/system-architecture.md).

| Directory | Purpose |
| --- | --- |
| `backend/` | FastAPI routes, schemas and cached services |
| `data/raw/` | Ignored local source CSV and provenance notes |
| `data/processed/` | Ignored cleaned/features/split CSVs |
| `docs/` | Architecture, methodology and reproduction guides |
| `ml/src/` | Shared research, persistence and inference helpers |
| `ml/notebooks/` | Recorded analyses and explanations |
| `ml/results/` | Committed numerical results, schemas, metadata and audits |
| `ml/models/` | Ignored canonical native model and usage notes |
| `src/` | Existing React/TanStack Start SSR application |
| `tests/` | Python, Node client and local browser/QA checks |

## Local installation and startup

Run from repository root using Python compatible with the recorded model environment (Python 3.13.14), Node supporting native TypeScript stripping, and npm or the existing Bun package workflow. Phase 30 verifies a separate tracked-file copy and new dependency installation; exact numerical versions are recorded in [reproduction](docs/reproducibility.md). Dependencies are partly unpinned, so a generic install is not an exact environment lock.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install "numpy==2.5.4" "pandas==3.0.6" "scikit-learn==1.9.1" "xgboost==3.4.1"
```

Use the recorded numerical versions for matching artifact loading/regeneration; do not weaken version/checksum guards. For absent frontend dependencies, the verified npm fallback is:

```powershell
npm install --package-lock=false
```

This resolves package ranges, not `bun.lock`; it does not promise the identical original tree. Preserve both package-management state and the Lovable wrapper. Do not regenerate/delete lockfiles.

### Required local artifacts

| Item | Required for | Provisioning / Git policy |
| --- | --- | --- |
| `ml/models/final_xgboost_model.json` | Forecasting and healthy model resources | Ignored; restore matching artifact privately or deliberately regenerate below |
| `data/raw/energydata_complete.csv` | Explicit ADMIN UCI reference import; research preparation | Download UCI dataset separately; ignored; not needed for manual/CSV application startup |
| Processed cleaned/features/TRAIN/VALIDATION/TEST CSVs | Research reproduction, artifact reconstruction, optional development example and comprehensive research QA | Generated by documented preparation scripts; ignored; not normal runtime requirements |
| `smartenergy.db` | Local account/building/history persistence | Generated empty by migrations; ignored; never copy an evaluator/developer DB into release |
| `ml/results/generated/*` | Optional QA/plots/logs | Generated, ignored; not runtime inputs |
| `.venv`, `node_modules` | Installed Python/frontend dependencies | Created locally, ignored |

The native model is intentionally not committed. If missing, [ordered reproduction](docs/reproducibility.md) explains downloading raw data, generating matching processed splits and restoring the recorded environment. Then:

```powershell
python ml/src/save_final_model.py
```

This reconstructs the **locked** TRAIN + VALIDATION fit, checks original Phase 11 equivalence and refuses differing existing model/metadata/audit outputs. It is not tuning or routine startup. It accesses TEST only for historical equivalence. Phase 30 does not refit/re-evaluate the authoritative model. Do not force-add model/data or rewrite numerical records to accept a different environment.

### Initialize and verify

```powershell
python tests/verify_demo_preflight.py
python -m alembic upgrade head
python -m alembic current
python scripts/create_admin.py
```

Preflight checks imports, model/schema/checksum, migration head, parseable DB configuration, frontend scripts and critical docs **without connecting to DB, fitting, reading datasets or repairing anything**. It does not prove migrations were applied or an ADMIN exists; those are explicit steps. The bootstrap prompts for your own email/name and hidden password/confirmation; no default credentials or startup seed exists. Duplicate accounts are rejected without promotion/overwrite.

`DATABASE_URL` defaults to `sqlite:///./smartenergy.db`, resolved relative to the project root. Keep connection secrets private. Existing populated data should be backed up before migrations. Current head is `0026_prediction_feature_snapshots`.

### Start services

Backend terminal:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
npm run dev -- --host localhost --port 5173 --strictPort
```

Use browser/API **localhost consistently**: [application](http://localhost:5173), [health](http://localhost:8000/health), [Swagger](http://localhost:8000/docs), [OpenAPI](http://localhost:8000/openapi.json). Binding the backend to IPv4 loopback does not change those browser URLs. `VITE_API_BASE_URL` defaults to `http://localhost:8000`; no environment file is needed. For other origins, deliberately configure the public build-time API URL and exact credentialed `SMARTENERGY_CORS_ORIGINS`; align HTTPS/Secure cookies. A development server is not a public production host.

### Use the application

Signup/login, create/edit a building, enter one actual measurement or import compatible observed history, then inspect readiness. The latest continuous **1,009 ten-minute observations** produce all 42 features server-side. Click **Predict next 10 minutes**, inspect recommendation/dashboard/history, and repeat identical input to demonstrate reuse. New history requires an explicit new forecast; prior snapshots remain historical. Select another owned building to demonstrate isolation.

For an immediately ready historical ADMIN demo, with the local UCI source present:

```powershell
python scripts/import_uci_reference_building.py --admin-email <your-admin-email>
```

Replace the placeholder with your existing active ADMIN. Import is explicit/atomic and repeated populated-reference imports are rejected. ADMIN uses its ordinary dashboard for its own reference building and dedicated `/admin` views for cross-owner oversight. No silent fake data appears. See [CSV contract](docs/measurement-import.md), [readiness](docs/prediction-readiness.md), [forecast lifecycle](docs/building-predictions.md), [dashboard](docs/user-dashboard.md) and [admin](docs/admin-panel.md).

## APIs, testing and final QA

[Current route/API inventory](docs/final-endpoint-inventory.md) lists every documented method/path from OpenAPI and every reachable file route. Public research POSTs accept all 42 engineered values; private building forecasts instead construct them from owned stored history. These are distinct contracts.

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
node --experimental-strip-types --test tests/frontend_*.test.mjs
node node_modules/typescript/bin/tsc --noEmit
npm run build
git diff --check
```

The unittest command uses runtime requirements without a separate pytest install. Optional `python -m pytest -q` needs pytest installed separately. Comprehensive research tests also require local raw/processed datasets and model; do not mistake their prerequisites for normal runtime requirements. Native Node tests use the existing test files and runner. Targeted semantic lint disables only formatting enforcement; repository-wide formatting debt is not release work.

`python tests/verify_final_application.py` is the Windows/installed-Edge release browser verifier. It uses a fresh disposable migrated DB, supported bootstrap and real UI/API journeys, blocks external page requests, and cleans its own processes/profile/DB. It requires the raw UCI CSV and `websocket-client` (included transitively by the current Jupyter installation); evidence stays ignored. Original feature/model/recommendation helpers provide separate parity gates. [Phase 29 security QA](docs/security-and-quality-assurance.md) and [Phase 30 final audit](ml/results/phase30_final_fullstack_audit.json) record actual results and warnings; historical audits describe their original phase snapshots.

## Limitations and final demo

- One UCI building, January-May and one later TEST period; transfer to other buildings is experimental.
- No true occupancy input or IoT streaming; measurements are manually entered/imported and require continuous ten-minute history. Observation timestamps are naive source-local; audit timestamps are naive UTC.
- No automatic scheduler/actuator/control, verified intervention savings or calibrated prediction intervals. Predictive importance is not causality; R-squared is not percentage accuracy.
- No MFA/rate limiting/email recovery delivery/central audit service or production-security certification. SQLite serializes writes; PostgreSQL driver/deployment/live concurrency remain unverified. Already-authorized requests can finish after revocation.
- Dependencies are partly unpinned; exact numerical/model regeneration remains environment-sensitive. Keep original results/checksums authoritative.

Use [demo guide](docs/thesis-demo-guide.md), [live checklist](docs/final-demo-checklist.md), [fact sheet](docs/project-fact-sheet.md), [defense answers](docs/defense-technical-reference.md), [architecture](docs/system-architecture.md) and [database schema](docs/database-architecture.md). The research and application are Bachelor-scope work; local demo readiness is distinct from commercial production readiness.

## Dataset reference

UCI Machine Learning Repository, *Appliances Energy Prediction*, DOI [10.24432/C5VC8G](https://doi.org/10.24432/C5VC8G). Source CSV is downloaded separately to `data/raw/energydata_complete.csv`; original retrieval timestamp/version was not recorded. [Provenance](data/raw/README.md) and recorded inspections preserve actual findings. No additional bibliographic fields are assumed.
