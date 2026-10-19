# SmartEnergyAI API

Phase 15 exposes the existing Tuned XGBoost model and forecast-based decision support. Use the project `.venv` with `requirements.txt` installed. The canonical ignored model artifact and matching Phase 13 metadata must already be available; the API never retrains or substitutes a model. Phase 14 thresholds must also exist. Missing or invalid resources produce HTTP 503 with a useful message.

Run from the project root:

```powershell
.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Default address: `http://127.0.0.1:8000`. Swagger: `http://127.0.0.1:8000/docs`; OpenAPI: `/openapi.json`. API title/version: SmartEnergyAI API / 1.0.0.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | API identification |
| GET | `/health` | Model/threshold availability without prediction |
| GET | `/model/info` | Safe model metadata, ordered feature names and existing Phase 11 metrics |
| POST | `/forecast` | One forecast |
| POST | `/forecast/recommendation` | One forecast with the unchanged Phase 14 recommendation structure |
| GET | `/recommendations/thresholds` | Development-only thresholds and exact level definitions |

Both POST routes accept `{"features": {"Appliances": ..., "lights": ..., ...}}` containing **exactly all 42 engineered feature names** listed by `/model/info` and `ml/results/feature_schema.json`. This abbreviated illustration is not a complete request. Numeric JSON integers and floats are accepted; numeric strings, booleans, null, missing/extra fields and nonfinite numbers are rejected. JSON key order is irrelevant: the service constructs the committed internal model order and uses the existing strict inference validator. Current Appliances must be nonnegative. One observation per request; batch input is rejected.

Generate a complete local request using an existing development row (never a fabricated history):

```python
import json
from pathlib import Path
import pandas as pd
schema = json.loads(Path("ml/results/feature_schema.json").read_text())
row = pd.read_csv("data/processed/energy_train.csv", nrows=1, float_precision="round_trip")
payload = {"features": row[schema["model_feature_columns"]].iloc[0].to_dict()}
# Pass payload as JSON to POST /forecast or POST /forecast/recommendation.
```

Forecast response fields: `prediction_wh`, `forecast_horizon_minutes`, `target`, `unit`. The target is `target_appliances_next`, Appliances energy in **Wh, 10 minutes ahead**. Predictions are not clipped and no confidence intervals are invented. Recommendation response contains `prediction`, `thresholds_wh`, `trend`, `recommendation` and `scope`, matching Phase 14 directly. Phase 14 rejects negative forecasts; such a model-output failure returns a generic 500 rather than changing the model or clipping its result.

The caller must supply real origin-time readings and valid historical lags/rolling statistics. The API does not create a time-series buffer, infer missing history, or expose a raw-sensor forecast endpoint. Recommendations are decision support only, with no automatic equipment control, causal sensor attribution, estimated savings or guaranteed savings. No database or authentication is included. The server defaults to loopback access.

Resources load lazily and successful loads are cached per process, so imports and API docs remain available when model files are absent. Failed loads are not cached and can be retried after files are restored. Health reports 503 when either model or thresholds are unavailable; forecasting can still work if only thresholds are missing. Health checks cached usability; it does not continuously re-hash loaded artifacts. Restart after intentional artifact changes.

CORS permits `http://localhost:3000`, `http://localhost:5173` and `http://localhost:8080` by default, with GET/POST and Content-Type only, without credentials. Optionally replace the list through comma-separated `SMARTENERGY_CORS_ORIGINS`; no `.env` is required. Wildcards are excluded.

Validation errors return 422. Unavailable/mismatched resources return 503. Unexpected inference/response failures return a generic 500 without filesystem paths or stack traces. Server logs retain diagnostic details.

Tests use FastAPI TestClient (`httpx` is required for tests):

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_api.py" -v
```


Phase 17 adds read-only `/analysis/model-comparison` (committed Phase 10 VALIDATION metrics and the existing Phase 11 selection lock) and `/analysis/feature-importance` (saved Phase 12 gain/permutation results). These endpoints do not load datasets or models, compute new rankings, refit, evaluate, or recompute importance. Normalized gain is a predictive fraction, not an energy share or causal effect. Permutation mean/std retain their recorded Wh interpretation; std is not a confidence interval.
