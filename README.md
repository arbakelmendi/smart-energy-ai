# SmartEnergyAI

**Artificial Intelligence for Prediction and Optimization of Energy Consumption in Smart Buildings**

SmartEnergyAI is a Bachelor-thesis research prototype for **10-minute-ahead Appliances energy prediction in Wh** and transparent **forecast-based decision support**. It combines a reproducible Python workflow, a persisted Tuned XGBoost model, FastAPI, and the existing React/TypeScript TanStack Start dashboard.

The objective is to compare forecasting approaches chronologically, estimate later-period performance and turn forecasts into conservative review recommendations. Optimization means decision support here, not automatic building control or validated intervention savings.

## Implemented capability and scope

- Predict `target_appliances_next`: information available at or before t predicts `Appliances` at t+1, ten minutes later. Current `Appliances_t` is a known input.
- Separate validation model comparison from the selected final model's held-out test performance.
- Explain predictive behavior with saved gain and permutation importance.
- Return deterministic recommendations calibrated on TRAIN + VALIDATION only.
- Present API-sourced research results with explicit loading/error/unavailable states.

No operational sensor/history stream is connected. The browser cannot fabricate historical lag/rolling context for a live forecast. Phase 22 provides real account authentication over the Phase 21 database foundation. Email delivery, occupancy inference and equipment control are unavailable; research endpoints remain database-independent. No guaranteed energy, monetary or CO2 savings or calibrated prediction intervals are claimed.

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

From the project root, on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Download the dataset separately to **`data/raw/energydata_complete.csv`**; do not commit it. Use the [ordered reproduction guide](docs/reproducibility.md) to generate processed data. Requirements are unpinned: a generic install does not guarantee exact replay. The guide lists recorded versions and separates verification from commands that refit models.

Inference requires **`ml/models/final_xgboost_model.json`**, ignored by Git. Once processed splits and committed records exist, its generator is:

```powershell
python ml/src/save_final_model.py
```

This refits the locked development configuration, checks Phase 11 equivalence and refuses differing existing outputs. It is not a lightweight load operation. Do not force-add its output. Verify an existing artifact without fitting:

```powershell
python -c "from ml.src.model_inference import load_final_model; load_final_model(); print('Verified model loaded')"
```

Start FastAPI in one terminal:

```powershell
.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Swagger: [http://localhost:8000/docs](http://localhost:8000/docs); OpenAPI: `/openapi.json`. See [backend usage](backend/README.md).

The existing frontend scripts are `dev: vite dev` and `build: vite build`. Phase 18 used installed dependencies and npm because Bun was unavailable. If `node_modules` is absent, `npm install --package-lock=false` is an npm fallback that resolves package ranges, not the Bun lock. It is not a claim of exact locked-tree reproduction. Preserve the existing package-management files; no install is needed for an existing dependency tree.

```powershell
npm run dev -- --host localhost --port 5173 --strictPort
```

Open [http://localhost:5173/dashboard](http://localhost:5173/dashboard). Public build-time `VITE_API_BASE_URL` defaults to `http://localhost:8000`; no environment file is required. See [frontend/API notes](src/lib/api/README.md).

### API overview

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | API identity |
| GET | `/health` | Resource availability without prediction |
| GET | `/model/info` | Final model and original held-out metrics |
| GET | `/recommendations/thresholds` | Development-only bands |
| GET | `/analysis/model-comparison` | Saved validation metrics |
| GET | `/analysis/feature-importance` | Saved predictive importance |
| POST | `/forecast` | Engineered observation -> Wh forecast |
| POST | `/forecast/recommendation` | Forecast and decision support |

POST body: `{"features": {...}}`, containing all 42 real engineered values. Missing history is rejected, not invented. JSON keys are ordered internally; direct inference DataFrames must already use the committed order.

## Testing, QA and reproducibility

[Phase 18 QA](ml/results/phase18_quality_assurance.json) records **66 Python and 20 frontend tests passed**, successful production build/TypeScript, and **19 routes** checked at **1440px/390px**. Live predictions/recommendations matched direct helpers. Offline, malformed input/response, model-unavailable and Retry states were verified.

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
node --experimental-strip-types --test tests/frontend_api.test.mjs
npm run build
node node_modules/typescript/bin/tsc --noEmit
python tests/verify_phase18.py
```

Optional Windows Edge route/browser QA: `python tests/verify_phase18.py --browser`; prerequisites are in the reproduction guide. Lint is **not perfectly clean**: Phase 18 recorded 956 targeted formatting findings. Semantic lint and `git diff --check` passed; no mass formatting was performed.

## Limitations and research integrity

- One building and January-May, including partial months: no full-year/multi-building generalization claim.
- No reliable occupancy input or operational sensor/history feed. Temperatures/humidity alone cannot provide valid engineered forecast inputs.
- Decision support, not automatic control; no validated intervention savings or calibrated prediction intervals.
- One later chronological test period; model/climate/building transfer requires further evidence. Importance is predictive and period-specific.
- Real cookie-backed authentication is implemented; email/reset services, building-specific inference and account management remain unavailable. Explicit local-development CORS/loopback assumptions are not production-grade security.
- Exact replay depends on input bytes, recorded libraries and serialization environment. Historical audits describe their phase snapshots, not immutable later application code.

Committed artifacts are the source of truth. Do not retune/select on TEST, rewrite results for a different environment, present research observations as live telemetry, or replace API failures with mock values. Preserve Lovable history and unrelated worktree changes.

## Thesis defense preparation

Use the [demo guide](docs/thesis-demo-guide.md), [technical reference](docs/defense-technical-reference.md) and [one-page fact sheet](docs/project-fact-sheet.md). Run `python tests/verify_demo_preflight.py` before starting the local servers. It verifies the existing model and a known development-data example without fitting or reading TEST. The final audit is recorded in [Phase 20](ml/results/phase20_final_audit.json).

## Dataset reference

UCI Machine Learning Repository. *Appliances Energy Prediction*. DOI: [10.24432/C5VC8G](https://doi.org/10.24432/C5VC8G). Retrieval date/version was not recorded locally. Saved [inspection](ml/notebooks/01_data_exploration.ipynb) and [EDA](ml/notebooks/02_exploratory_data_analysis.ipynb) provide local findings. No additional bibliographic fields are assumed.

## Application database foundation (Phase 21)

An independent SQLAlchemy/Alembic schema now supports users, owned buildings, raw measurements and prediction/recommendation snapshots. See [database architecture and initialization](docs/database-architecture.md). SQLite defaults to an ignored repository-local `smartenergy.db`; initialize an empty schema with `python -m alembic upgrade head`. This adds no authentication, import or CRUD/persistence endpoints. Existing research routes/dashboard remain database-independent. Earlier phase documents describe their verified historical scope.

## Real authentication (Phase 22)

Initialize/upgrade the database with `python -m alembic upgrade head`, optionally create the first administrator with `python scripts/create_admin.py` (hidden password prompt), then start FastAPI and the frontend as above. Use **localhost** consistently in browser/API URLs. Signup/login now establish persistent HttpOnly-cookie sessions; application pages require a session and admin routes require ADMIN. Public research APIs remain accessible without login. See [authentication configuration, security boundaries and verification](docs/authentication.md). Earlier phase demo/database documents describe historical scope; this authentication workflow supersedes their account-free application access.

## Building management (Phase 23)

Signed-in users can create, list, view, edit and delete their own building metadata at `/buildings`. ADMIN follows the same owner-only policy in this phase. Existing database schema/authentication are reused; run the normal migration/startup commands, then sign in. No measurements, reference building, building-specific forecasting or model validation are created by adding metadata. See [building management](docs/building-management.md) for endpoints, validation, deletion cascades and verification.

## Building measurement history (Phase 24)

Owned buildings now support raw manual measurements, paginated persisted history and atomic CSV uploads. The explicit active-ADMIN reference importer reads the existing local UCI source without changing it. Install updated requirements for `python-multipart`. See [measurement import](docs/measurement-import.md) for fields/units, timezone-naive timestamp policy, CSV header, commands, ownership and verification. Counts do not establish ML readiness; building-specific feature construction and forecasting remain deferred.

## Automatic feature construction and readiness (Phase 25)

Building detail now checks the latest required ten-minute history and constructs the exact 42-feature input internally using shared finalized research formulas. Readiness requires 1,009 observations, not a count-only threshold. The owner-only readiness API runs no model and stores no features or predictions. See [prediction readiness](docs/prediction-readiness.md) for continuity policy, parity evidence and verification. Building forecasts remain deferred.
