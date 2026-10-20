# Thesis demo guide

[Fact sheet](project-fact-sheet.md) | [Technical reference](defense-technical-reference.md) | [Reproduction](reproducibility.md)

## Before the defense

Use the prepared local checkout, its installed dependencies and verified model. From the repository root in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python tests/verify_demo_preflight.py
python -m uvicorn backend.main:app --reload
```

Preflight loads/checks the existing native model and runs deterministic TRAIN-row inference; it never fits a model. If it fails, resolve the reported prerequisite before presenting. In a second terminal, from the same root:

```powershell
npm run dev -- --host localhost --port 5173 --strictPort
```

Check [health](http://127.0.0.1:8000/health) and [model information](http://127.0.0.1:8000/model/info). Open [dashboard](http://localhost:5173/dashboard), [about](http://localhost:5173/about) and optionally [Swagger](http://127.0.0.1:8000/docs). Confirm research panels load; backend availability does not mean sensors are connected. Keep both terminals visible for startup errors. Do not install dependencies or regenerate research outputs during the defense.

## Suggested sequence (about 5-8 minutes)

1. Show the public overview/about and dashboard: one-building research prototype, next-interval energy forecasting plus transparent decision support.
2. Identify Tuned XGBoost, the ten-minute horizon, Wh and the 42-feature input contract. State that the final fit uses TRAIN + VALIDATION.
3. Show the validation comparison: six configurations across four approaches. Lowest validation RMSE selected the model before TEST access.
4. Show held-out TEST MAE/RMSE/R-squared, explicitly distinguished from validation. Use the [fact sheet](project-fact-sheet.md) for exact values; these describe one later period, not accuracy percentages.
5. Explain top-ten gain importance as predictive model reliance. It does not identify causal savings actions; permutation interpretation is in the methodology record.
6. Show development-calibrated recommendation bands on `/recommendations`: 100/190/320 Wh boundaries. These guide safe review of flexible loads and do not control equipment.
7. Point out the live-history limitation on predictions/recommendations: no operational sensor/history feed supplies the required current readings, lags and rolling values. The UI does not fabricate forecasts.
8. Optionally demonstrate `/forecast` in Swagger using the **known development-data example** below. Say that it is an observed historical TRAIN row, already within development, not live data or a new performance estimate.
9. Optionally submit the same body to `/forecast/recommendation` and explain its band, trend and scope fields. No intervention or savings measurement follows.

## Optional known development-data example

Generate the request from the first actual engineered TRAIN observation, in schema order:

```powershell
python tests/verify_demo_preflight.py --development-request
```

This prints only the JSON body for copying into Swagger's `features` request. It reads `data/processed/energy_train.csv`, never TEST. The first origin is 2016-01-18 17:00:00 according to committed split metadata. Do not relabel it as current or representative deployment performance. Both POST endpoints require all 42 engineered numeric values. Keep the result as a technical demonstration; do not copy it into frontend fallback data.

## Claims to avoid

No automatic HVAC/equipment control, guaranteed or measured intervention savings, multi-building validation, live sensor integration, calibrated confidence/prediction intervals, occupancy prediction or causal feature effects. The prototype has no real account/database service. Wh is energy over an interval, not instantaneous power.

## Recovery

- Backend unavailable: inspect its terminal; verify the activated Python and run preflight. Check port 8000 and `/health`. Restart the documented command, then use panel Retry. Do not replace errors with mock values.
- Model absent/hash mismatch: stop the forecast demo. Restore the original matching local artifact from the prepared checkout. Deliberate regeneration is documented in [reproduction](reproducibility.md), requires the recorded environment and refits the locked model; it is not a defense-time recovery command. Never weaken checksum guards.
- Frontend unavailable: inspect its terminal, confirm root working directory, installed `node_modules` and free port 5173. Restart the exact command with `--strictPort`. Do not kill unrelated processes. For an unexpected origin, consult documented CORS configuration.
- If the UI cannot be restored, show the committed fact sheet/methodology and, if available, the real Swagger API. Clearly state what is unavailable; do not imply the fallback documents are a running dashboard.
- Stop each server with Ctrl+C after the demonstration. QA servers are temporary and are stopped after checks; start these two terminals yourself before presenting.
