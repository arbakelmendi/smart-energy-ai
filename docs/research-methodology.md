# Finalized research methodology

[Overview](../README.md) | [Architecture](system-architecture.md) | [Reproduction](reproducibility.md)

This technical record describes completed Phases 2-14, not a new experiment or a thesis chapter.

## Validation, EDA and preprocessing (Phases 2-4)

UCI *Appliances Energy Prediction*, DOI [10.24432/C5VC8G](https://doi.org/10.24432/C5VC8G), is the sole initial dataset. Saved [inspection](../ml/notebooks/01_data_exploration.ipynb) and [EDA](../ml/notebooks/02_exploratory_data_analysis.ipynb) establish **19,735 rows, 29 raw columns**, coverage **2016-01-11 17:00:00 to 2016-05-27 18:00:00**, and exact ten-minute continuity. Recorded missing values, duplicate rows, duplicate timestamps and invalid dates are zero. No timezone conversion or synthetic occupancy is introduced.

EDA describes energy distributions, time patterns, environmental associations, lighting and unusual observations. Correlation is not intervention evidence. The whole-dataset peak percentile is exploratory only, not production recommendation calibration or model-selection evidence.

[Preprocessing](../ml/src/preprocess.py) removes only the identical random/questionable `rv1` and `rv2` columns. It retains source rows and target outliers, checks chronology/uniqueness/continuity and preserves raw bytes. No gap imputation, occupancy synthesis or target clipping is applied.

## Objective and origin-time features (Phase 5)

At t, use observations available at or before t to predict `target_appliances_next = Appliances_(t+1)`, ten minutes later. Current `Appliances_t` remains known input. Wh is interval energy, not instantaneous power.

The [schema](../ml/results/feature_schema.json) fixes 42 predictors:

| Family | Definition |
| --- | --- |
| Current readings | Appliances, lights, recorded temperature/humidity and outdoor/weather values at t |
| Temporal | Integer hour, weekday, month and weekend indicator at origin |
| Cyclical | Sine/cosine of integer hour and weekday; Monday is weekday zero |
| Consumption history | `appliances_lag_1`, `_6`, `_144`, `_1008` |
| Rolling | Trailing one-hour/six-observation and 24-hour/144-observation mean and sample standard deviation |

Lags are relative to **forecast origin**, not target time: lag 1 uses t-1 (ten minutes before t); lag 6 uses one hour before t; lag 144 uses 24 hours before t; lag 1008 uses seven days before t. Full rolling windows include t and earlier readings only; sample standard deviation uses ddof=1. Only the target is shifted forward. Date and target are not model input columns.

The first 1008 rows lack seven-day context and the final row lacks its next target. The result is **18,726 supervised samples**, each with 42 features plus date and target. These are alignment exclusions, not outlier cleaning. See [implementation](../ml/src/feature_engineering.py) and [recorded feature checks](../ml/notebooks/04_feature_engineering.ipynb).

## Chronological partition and leakage controls (Phase 6)

Nominal partitions are 70/15/15, contiguous and unshuffled:

| Split | Rows | First forecast origin | Last forecast origin |
| --- | ---: | --- | --- |
| TRAIN | 13108 | 2016-01-18 17:00:00 | 2016-04-18 17:30:00 |
| VALIDATION | 2809 | 2016-04-18 17:40:00 | 2016-05-08 05:40:00 |
| TEST | 2809 | 2016-05-08 05:50:00 | 2016-05-27 17:50:00 |

These are **forecast-origin timestamps**; each target is ten minutes later. No embargo is added between partitions. The last training target can coincide with the first validation origin's already-known current observation, but it is not a validation next-step target. Target-time ranges remain disjoint across partitions. Do not describe this as a purged/gapped split. TimeSeriesSplit uses its implemented default gap, while each feature remains current/past-only.

TRAIN fits parameters and preprocessing. VALIDATION supports post-CV comparison. TEST is excluded from candidate fitting, tuning and selection. Linear Regression scales within its TRAIN-fitted pipeline; trees require no scaler. [Split metadata](../ml/results/split_metadata.json) records input checksums, exact boundaries and ordering checks.

## Required models and tuning (Phases 7-10)

Persistence predicts the next interval using current `Appliances_t`. Linear Regression uses StandardScaler fitted only on TRAIN. Untuned Random Forest and XGBoost are initial tree baselines. Tree tuning uses **5 expanding TimeSeriesSplit folds within TRAIN**. Each tree candidate is selected by lowest mean CV RMSE, refitted on TRAIN, then evaluated on VALIDATION. Seeds, candidate profiles and fold boundaries are in [Phase 10 summary](../ml/results/phase10_tuning_summary.json) and [candidate audit](../ml/results/phase10_tuning_cv_results.json).

### Saved VALIDATION results

| Model | Validation MAE (Wh) | Validation RMSE (Wh) | Validation R-squared |
| --- | ---: | ---: | ---: |
| Persistence Baseline | 25.920256318974722 | 65.79497157144202 | 0.46527285610821445 |
| Linear Regression | 27.02529387063962 | 59.346237268480074 | 0.5649559830358953 |
| Untuned Random Forest | 53.004521181915266 | 100.81836183251377 | -0.25552711394804195 |
| Tuned Random Forest | 33.03036877970391 | 64.50352076663437 | 0.4860585286448823 |
| Untuned XGBoost | 54.392578125 | 90.57733660386576 | -0.013411760330200195 |
| Tuned XGBoost | 25.493202209472656 | 57.62563762187907 | 0.5898163318634033 |

These are six validation estimates, not six final test evaluations. Final ranking uses lowest validation RMSE; exact ties use alphabetical model name. MAE and R-squared are supporting measures. The [selection lock](../ml/results/phase11_selection_lock.json) records this exact rule; it must not be changed retrospectively.

## Final model and held-out evaluation (Phase 11)

**Tuned XGBoost** was selected with validation RMSE **57.62563762187907 Wh**, before TEST access. The fixed model was fitted on TRAIN + VALIDATION (15,917 rows), excluding TEST. No early stopping on TEST or post-test tuning occurred.

Locked parameters from committed metadata:

```json
{
  "colsample_bytree": 1.0,
  "learning_rate": 0.03,
  "max_depth": 3,
  "min_child_weight": 5,
  "n_estimators": 100,
  "n_jobs": 1,
  "objective": "reg:squarederror",
  "random_state": 42,
  "subsample": 1.0,
  "tree_method": "hist",
  "verbosity": 0
}
```

These are explicit locked parameters; other defaults depend on the recorded library version. Only this selected model has the [final held-out estimate](../ml/results/phase11_final_test_evaluation.json):

| Held-out TEST metric | Exact Phase 11 value |
| --- | ---: |
| MAE (Wh) | 25.891124725341797 |
| RMSE (Wh) | 59.11701146812037 |
| R-squared (dimensionless) | 0.5820133686065674 |

Test RMSE exceeds validation RMSE by **1.491373846241295 Wh**. This is descriptive, not a confidence interval. One later period from the same building does not establish generalization to other buildings, climates or an entire year.

## Explainability (Phase 12)

[Saved importance](../ml/results/phase12_feature_importance.json) provides:

- **Gain:** average training-objective gain across splits using a feature, normalized by the sum of per-feature average gains. The booster was fitted on TRAIN + VALIDATION.
- **Permutation:** full held-out TEST, interpreted after model selection. Importance is permuted RMSE minus reference RMSE in Wh; negative results remain negative. There are 10 repetitions with seed 42.

Top saved gain features:

| Feature | Normalized gain fraction |
| --- | ---: |
| `Appliances` | 0.38923386017745365 |
| `appliances_lag_1` | 0.05394192425510965 |
| `T6` | 0.0424866940672054 |
| `appliances_roll_mean_1h` | 0.03499040190676228 |
| `hour` | 0.0302585806120196 |

Current/historical consumption is prominent, but gain and permutation rankings differ. Correlated inputs can substitute or mask reliance; independent permutations disrupt temporal and cross-feature consistency. Repeat standard deviation is **not a confidence interval**. Importance is predictive, not causal, and does not measure physical energy shares or intervention savings. No feature selection or new development decisions follow TEST interpretation. SHAP remains deferred.

## Persistence (Phase 13)

`ml/models/final_xgboost_model.json` is native XGBoost JSON, ignored by Git. [Final metadata](../ml/results/final_model_metadata.json) records feature order, dependencies, parameters, checksum and original metrics. [Persistence verification](../ml/results/phase13_model_persistence.json) records reconstruction/equivalence and reload behavior.

Generation reconstructs the fixed development fit and requires Phase 11 equivalence before saving. It compares deterministic candidate bytes, preserves matching existing files and refuses differing outputs. Production inference only loads/verifies; it does not fit or read datasets. Technical replay does not select another model or replace the authoritative evaluation.

## Forecast-based decision support (Phase 14)

[Threshold metadata](../ml/results/phase14_recommendation_thresholds.json) uses TRAIN + VALIDATION `target_appliances_next` values only (15,917 rows). Linear percentiles: p50=60, p75=100, p90=190, p95=320 Wh. p50 is descriptive. TEST and the whole-dataset EDA cutoff do not calibrate rules.

| Level | Forecast band (Wh, next 10 minutes) | Stable code |
| --- | --- | --- |
| NORMAL | prediction < 100 | NORMAL_CONSUMPTION |
| ELEVATED | 100 <= prediction < 190 | ELEVATED_CONSUMPTION |
| HIGH | 190 <= prediction < 320 | HIGH_CONSUMPTION |
| VERY HIGH | prediction >= 320 | VERY_HIGH_CONSUMPTION |

NORMAL reports no immediate warning. ELEVATED suggests reviewing flexible/non-essential loads where appropriate. HIGH suggests checking discretionary demand that can safely be delayed/reduced. VERY HIGH flags an unusually high development-relative forecast and suggests safe review of controllable non-critical loads. No essential-equipment shutdown or sensor-specific causal action is prescribed.

Trend is exact predicted-minus-current Wh with sign-based direction and no tolerance. Percentage change is returned only for positive current energy. Trend explains, but does not change, the main level. Invalid energy, malformed input or missing metadata fails explicitly. Batch recommendations preserve row order.

This is deterministic decision support, not optimal control, scheduling or dispatch. Band effectiveness/interventions have not been operationally validated. Savings, occupancy, comfort scores and confidence intervals are not fabricated. [Phase 14 audit](../ml/results/phase14_recommendation_engine.json) records scope and verification.
