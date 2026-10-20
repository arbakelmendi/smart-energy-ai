# SmartEnergyAI project fact sheet

[Demo guide](thesis-demo-guide.md) | [Technical reference](defense-technical-reference.md) | [Methodology](research-methodology.md)

| Item | Verified fact |
| --- | --- |
| Dataset | UCI Appliances Energy Prediction; DOI 10.24432/C5VC8G; one building |
| Raw observations | 19,735 rows, 29 columns; 2016-01-11 17:00:00 through 2016-05-27 18:00:00; exact ten-minute spacing |
| Preparation | Remove identical random rv1/rv2; retain source rows/outliers; 18,726 aligned supervised rows, 42 predictors |
| Target | `target_appliances_next`: Appliances Wh one interval (10 minutes) ahead |
| Chronological partitions | TRAIN 13,108; VALIDATION 2,809; TEST 2,809; no shuffle; final development fit 15,917 |
| Candidates | Persistence, Linear Regression, Random Forest and XGBoost; six validation configurations including untuned/tuned trees |
| Selection | Tuned XGBoost; lowest validation RMSE; exact ties alphabetical name; five expanding TRAIN-only CV folds support tuning |
| Selected VALIDATION | MAE 25.493202209472656 Wh; RMSE 57.62563762187907 Wh; R-squared 0.5898163318634033 |
| Final held-out TEST | MAE 25.891124725341797 Wh; RMSE 59.11701146812037 Wh; R-squared 0.5820133686065674 |
| Development-only percentiles | p50=60, p75=100, p90=190, p95=320 Wh; 15,917 target observations |
| Recommendation bands | NORMAL <100; ELEVATED 100 to <190; HIGH 190 to <320; VERY HIGH >=320 Wh |
| Top normalized gain features | Appliances 0.38923386017745365; appliances_lag_1 0.05394192425510965; T6 0.0424866940672054; appliances_roll_mean_1h 0.03499040190676228; hour 0.0302585806120196 |
| Backend/research | Python, Pandas, NumPy, scikit-learn, XGBoost native JSON, FastAPI/Pydantic/Uvicorn; shared strict inference/recommendation helpers |
| Frontend | React/TypeScript, TanStack Start SSR/file routes, Vite, Tailwind, TanStack Query and existing Recharts components |
| Scope/limits | January-May single-building evidence and one later TEST period; no reliable occupancy input, operational sensor/history feed, automatic control, verified intervention savings, calibrated intervals, real authentication/database or demonstrated external portability. Live inference needs all 42 engineered values. Exact regeneration is environment-sensitive with unpinned dependencies; historical formatting findings remain. |

Numerical sources: [schema](../ml/results/feature_schema.json), [splits](../ml/results/split_metadata.json), [tuning](../ml/results/phase10_tuning_summary.json), [final evaluation](../ml/results/phase11_final_test_evaluation.json), [importance](../ml/results/phase12_feature_importance.json), [metadata](../ml/results/final_model_metadata.json), [bands](../ml/results/phase14_recommendation_thresholds.json). Raw dimensions/coverage are recorded in [inspection](../ml/notebooks/01_data_exploration.ipynb) and [provenance](../data/raw/README.md). Importance is predictive, not causal; Wh is interval energy, not power; R-squared is not percentage accuracy. A known development-data POST example is a historical demonstration, not live telemetry or a new evaluation.
