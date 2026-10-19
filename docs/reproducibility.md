# Reproducibility and local operation

[Overview](../README.md) | [Methodology](research-methodology.md) | [Architecture](system-architecture.md)

## Choose the intended operation

1. **Run the prototype:** restore local data/model prerequisites, verify an existing artifact, start backend/frontend. No fitting is needed when the verified artifact exists.
2. **Verify recorded behavior:** run inference checks, tests and optional browser QA. Do not regenerate results merely to launch or review the application.
3. **Reproduce research:** execute the ordered pipeline in an isolated copy with the recorded environment/input bytes. Some commands overwrite prepared/result files or refit models. Phases 11/12 deliberately refuse ordinary overwrites.

The commands below document the existing implementation. **Training, tuning, evaluation, environment installation and model generation were not executed in Phase 19.** Original results remain the source of truth; never delete/edit them to make a new environment pass a reproduction gate.

## Environment

Run from the repository root. Windows-first setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Activation is optional if each command uses `.venv\Scripts\python.exe`. On POSIX, use `source .venv/bin/activate` and `.venv/bin/python` equivalents. No machine-specific absolute paths or required `.env` file are used.

### Recorded numerical environment

Copied from [final model metadata](../ml/results/final_model_metadata.json):

| Component | Recorded version |
| --- | --- |
| Python | 3.13.14 |
| numpy | 2.5.4 |
| pandas | 3.0.6 |
| scikit-learn | 1.9.1 |
| xgboost | 3.4.1 |

`requirements.txt` is intentionally unpinned in the existing repository. A generic install may resolve a different environment; it does **not** establish exact research reproducibility. Provision the recorded Python first, and, when available, match the recorded numerical packages:

```powershell
python -m pip install "numpy==2.5.4" "pandas==3.0.6" "scikit-learn==1.9.1" "xgboost==3.4.1"
```

This installation command is documented, not executed or availability-tested in Phase 19. It is not a complete lock of every transitive dependency or OS/compiler detail. Production inference explicitly requires the recorded XGBoost version; exact numerical/serialization replay additionally needs unchanged input bytes and compatible recorded dependencies. Do not weaken checksum/equivalence guards or rewrite metrics if a version differs.

Frontend dependencies are described by [package.json](../package.json) and the retained [Bun lock](../bun.lock). QA used an already-installed `node_modules` and existing npm scripts because Bun was unavailable; no Bun command is claimed as locally verified. If dependencies are absent, an npm fallback that avoids creating/updating a package lock is:

```powershell
npm install --package-lock=false
```

This resolves package ranges, not the Bun lock, and does not guarantee an identical dependency tree. Preserve existing lockfiles and package-management conventions. Dependency download/installation was not performed in this documentation phase. Use a compatible Node version supporting the existing `--experimental-strip-types` test command; the build/scripts remain unchanged.

## Data placement and read-only validation

Download UCI *Appliances Energy Prediction*, DOI [10.24432/C5VC8G](https://doi.org/10.24432/C5VC8G), separately. Extract/place the CSV at **`data/raw/energydata_complete.csv`**. Preserve raw bytes and leave raw data ignored by Git. Recorded source findings are in [raw-data notes](../data/raw/README.md) and the inspection/EDA notebooks.

```powershell
python ml/src/check_dataset.py
```

This is read-only. The inspector intentionally flags identical `rv1`/`rv2` values; preprocessing removes those questionable columns. Its original generic units caution is not a different model target: the finalized feature/model contract uses Appliances Wh. The original download timestamp/version was not recorded, so match the locally recorded data checksums rather than assuming all exports are byte-identical.

## Ordered research pipeline

Use this sequence only for deliberate research reproduction, not routine application startup. Preserve original results and compare any generated changes. Preparation writes ignored CSVs; the splitter also writes committed schema/metadata. Baseline/tree/tuning scripts write numerical result JSON. A different environment may change bytes/results, which is a discrepancy to investigate rather than accept silently.

### Preparation (Phases 4-6)

```powershell
python ml/src/preprocess.py
python ml/src/feature_engineering.py
python ml/src/split_data.py
```

Outputs: `data/processed/energydata_cleaned.csv`, `energydata_features.csv`, and `energy_train.csv`, `energy_validation.csv`, `energy_test.csv`. The first two preserve current/past-only inputs and align the next-step target. Exact split boundaries and hashes are in [split metadata](../ml/results/split_metadata.json); ordered predictors are in [feature schema](../ml/results/feature_schema.json). Verify regenerated files against those records before proceeding. Do not force-add ignored CSVs.

### Baselines, tree models and tuning (Phases 7-10)

```powershell
python ml/src/train_baselines.py
python ml/src/train_random_forest.py
python ml/src/train_xgboost.py
python ml/src/tune_models.py
```

The baseline script implements persistence and TRAIN-only-scaled Linear Regression. Tree baseline scripts fit TRAIN and report VALIDATION metrics. Tuning uses TRAIN-only expanding CV, followed by VALIDATION comparison. These commands perform fitting; tuning can be expensive. They are not documentation validation commands and were not run in Phase 19.

### Final selection/evaluation (Phase 11)

The existing checkout contains the authoritative final result and selection lock. Its deliberate technical replay command is:

```powershell
python ml/src/evaluate_final_model.py --verify-reproducibility
```

It refits the fixed development configuration, replays held-out predictions/metrics and demands exact agreement. This is equivalence verification of the original workflow, not another model-selection experiment. Ordinary first-recording mode is `python ml/src/evaluate_final_model.py`; it is only appropriate for an explicitly authorized independent experiment with no original final record, not for deleting committed records to force a rerun.

The verification branch does **not** regenerate a missing ignored `ml/results/generated/phase11_test_predictions.csv`. Some diagnostic notebook loaders require that historical file. Restore the original matching diagnostic output when needed; do not promise that replay mode recreates every plot/CSV, or change committed metrics to work around an absent diagnostic.

### Explainability (Phase 12)

```powershell
python ml/src/explain_final_model.py --verify-reproducibility
```

Existing explanation results also block ordinary overwrite mode. Replay reconstructs the fixed model, requires Phase 11 equivalence, and recomputes the original post-hoc importance only for comparison. It can be expensive, accesses TEST for equivalence/interpretation, and must not influence model development. First-recording mode is `python ml/src/explain_final_model.py` only when producing an authorized original record. Neither command was run in this documentation phase.

### Native persistence (Phase 13)

```powershell
python ml/src/save_final_model.py
```

Canonical ignored output: **`ml/models/final_xgboost_model.json`**. Required prerequisites include processed splits and matching committed Phase 10-12 records. Generation reconstructs the locked TRAIN + VALIDATION fit, accesses TEST only for the existing Phase 11 equivalence gate, and verifies exact native reload predictions on the recorded TRAIN sample. It compares candidate model/metadata/audit bytes, preserves matching existing outputs, creates absent outputs at canonical paths and refuses differing existing ones. It does not retune or select features.

The local model file is required for inference. Do not force-add it or weaken ignore rules. To verify an already-present artifact **without fitting or dataset reads**:

```powershell
python -c "from ml.src.model_inference import load_final_model; load_final_model(); print('Verified model loaded')"
```

### Recommendations (Phase 14)

Read-only verification of existing thresholds against TRAIN + VALIDATION:

```powershell
python -c "from ml.src.recommendation_engine import calibrate_thresholds, load_thresholds; assert calibrate_thresholds() == load_thresholds(); print('Development thresholds verified')"
python -m unittest discover -s tests -p "test_recommendation_engine.py" -v
```

The existing generation command, `python -m ml.src.recommendation_engine`, writes threshold metadata. It is for deliberate deterministic regeneration, not necessary for checking or running the API. Boundary tests use synthetic scalar fixtures only, not fabricated research forecasts. Real notebook examples use existing development observations and are demonstrations, not generalization estimates.

## Run the local application

Backend, from the root:

```powershell
.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

On an activated environment/POSIX, `python -m uvicorn backend.main:app --reload` is equivalent. Swagger is [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs); schema is [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json).

Frontend, in a second terminal:

```powershell
npm run dev -- --host localhost --port 5173 --strictPort
```

Visit [http://localhost:5173/dashboard](http://localhost:5173/dashboard). The Vite scripts are taken from current `package.json`, not assumed SPA scaffolding. Keep TanStack Start SSR, root layout, server middleware and the Lovable wrapper intact. Do not intentionally regenerate or hand-edit `src/routeTree.gen.ts` for documentation.

Public build-time `VITE_API_BASE_URL` defaults to `http://127.0.0.1:8000`. No environment file is needed for that default. Backend local CORS allows localhost ports 3000/5173/8080 without credentials. For another browser origin, configure the existing comma-separated `SMARTENERGY_CORS_ORIGINS`; a remote browser also needs a reachable API and compatible HTTPS. This is not production-grade security or an authenticated service.

## Tests and QA

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
node --experimental-strip-types --test tests/frontend_api.test.mjs
npm run build
node node_modules/typescript/bin/tsc --noEmit
python tests/verify_phase18.py
```

The project uses unittest and the native Node runner; pytest was not installed for recorded QA. `httpx` supports FastAPI TestClient. Full integration tests need local datasets and the model; some artifact tests skip if the ignored model is absent, while other integration fixtures require it and fail rather than fabricate data. A checkout with only committed metadata is not sufficient for all integration tests.

Optional full Windows Edge browser QA:

```powershell
python tests/verify_phase18.py --browser
```

This uses installed Edge, `websocket-client` available in the recorded Jupyter environment, and free ports 8000/5173. Set `SMARTENERGY_BROWSER` for another installed executable. The current script is Windows-specific in process handling; no cross-platform browser runner is claimed. It starts/stops its own processes, blocks external page requests and checks all reachable routes at desktop/mobile widths, live endpoints, development-row POST equivalence, invalid inputs, malformed research responses, model absence, offline/retry and request-loop sanity. Logs/screenshots stay under ignored `ml/results/generated/`.

[Phase 18 audit](../ml/results/phase18_quality_assurance.json) records 66 Python and 20 frontend passes, 19 routes at 1440px/390px, successful build/TypeScript and safe E2E failures. It also records 956 targeted formatting findings. Semantic lint and whitespace checks passed; broad formatting was intentionally excluded. The existing Starlette/httpx deprecation and Vite build warnings are recorded, not hidden.

These are historical verified QA results. Phase 19 validates documentation paths/commands/links and integrity; it does not claim another full research or browser run. Exact byte equality remains environment-sensitive. Keep the initial held-out evaluation authoritative, never tune to TEST, and investigate discrepancies rather than rewriting reference outputs.
