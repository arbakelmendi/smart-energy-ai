# Defense technical reference

[Fact sheet](project-fact-sheet.md) | [Demo guide](thesis-demo-guide.md) | [Methodology and exact parameters](research-methodology.md)

| Question | Project-specific answer |
| --- | --- |
| What is predicted? | `target_appliances_next = Appliances_(t+1)`, Wh for the next ten-minute observation, from information available at/before origin t. |
| Why ten minutes? | The actual dataset has exact ten-minute spacing. This is the implemented one-step horizon; no hourly/day-ahead forecast was evaluated. |
| Why chronological, not random splits? | TRAIN 13,108, VALIDATION 2,809, TEST 2,809 retain temporal order and estimate a later period. Random allocation could train on later observations and mix temporally related histories across evaluation. |
| Why persistence? | Predicting the next value as current Appliances is a meaningful simple temporal benchmark. Its validation RMSE is 65.79497157144202 Wh. |
| Why did untuned trees perform badly? | Saved validation RMSE was 100.81836183251377 Wh for RF and 90.57733660386576 Wh for XGBoost, with negative R-squared. The initial configurations generalized poorly on this slice; tuning improved these results. No ablation establishes a single causal reason. |
| How was tuning performed? | Five expanding TimeSeriesSplit folds within TRAIN; lowest mean CV RMSE selected tree settings, then TRAIN refit and VALIDATION comparison. Seeds, candidate profiles and fold boundaries are saved in Phase 10; TEST was excluded. |
| Why TimeSeriesSplit? | Each fold fits earlier observations and validates later ones, preserving forecast direction instead of shuffling. Fold preprocessing must fit on its training portion. |
| Why did Tuned XGBoost win? | Lowest saved validation RMSE: 57.62563762187907 Wh. Validation MAE 25.493202209472656 Wh; R-squared 0.5898163318634033. Exact RMSE ties use alphabetical model name; supporting metrics do not replace that rule. |
| What does RMSE mean? | Square root of mean squared forecast error, in Wh. Squaring weights large errors more strongly than MAE. It is neither a confidence interval nor an accuracy percentage. |
| What does final R-squared mean? | 0.5820133686065674 = 1 minus squared residual sum divided by squared deviations from the TEST target mean. It measures error reduction relative to that constant reference on this period; it is not 58.2% accuracy or savings. |
| What are the final errors? | Held-out MAE 25.891124725341797 Wh and RMSE 59.11701146812037 Wh, recorded once after selection in Phase 11. |
| Why is current Appliances allowed? | It is observed at origin t, before predicting t+1. This assumes an actual deployment can supply that observation at forecast time; the application accepts persisted manual/CSV observations, without an IoT feed. |
| What is leakage; how is it prevented? | Using unavailable future information or evaluation data to fit/select a model. Only target shifts forward; lags/rolling use current/past values. Chronological partitions, TRAIN-only preprocessing/CV, validation-only comparison and locked selection precede TEST evaluation. |
| Are boundary labels purged? | No added embargo. The last TRAIN target may equal the first VALIDATION origin's already-known current value; next-step target ranges remain disjoint. Do not describe the split as purged/gapped. |
| Why remove rv1/rv2? | Recorded inspection found identical random/questionable columns. They do not represent defensible physical predictors; preprocessing removes both and preserves all source rows. |
| Why retain outliers? | High consumption can be real demand. No evidence establishes these target observations as erroneous, so clipping/removing them would change the forecasting problem. |
| What do lags mean? | Origin-relative lag 1/6/144/1008 uses t-1/t-6/t-144/t-1008: ten minutes/one hour/24 hours/seven days before origin, not before target time. Six/144-observation rolling windows include origin; sample std uses ddof=1. |
| What does importance mean? | Normalized average split gain from the development-fitted booster; saved permutation importance is the increase in held-out RMSE after shuffling a feature (10 repeats, seed 42). Rankings differ. |
| Why is importance not causality? | Predictive reliance and associations do not measure the outcome of intervening on a feature. Correlated features can substitute and independent permutation disrupts temporal consistency. Repeat std is not a confidence interval. |
| Why recommendations, not automatic optimization? | Deterministic forecast bands from development target percentiles support safe review of flexible/non-essential loads. No equipment dispatch, optimizer, intervention experiment or measured savings is implemented. |
| Why TEST only after selection? | Keeping it outside fitting, tuning and ranking preserves a later-period performance estimate. Post-hoc Phase 12 TEST interpretation and historical equivalence checks did not change development choices; they are not new selection experiments. |
| Why exclude TEST from production fitting? | The persisted model matches the evaluated TRAIN + VALIDATION fit (15,917 rows). Adding TEST would change that model and invalidate attributing the original held-out estimate to it. |
| Main limitations? | One building, January-May only, one later-period TEST, no reliable occupancy input or IoT stream, continuous history required for 42 features, no control/verified savings/intervals; real authentication/database are implemented, unpinned dependencies and historical formatting debt. External portability is unestablished. |
| Future research? | Independently validate other seasons/buildings, implement a verified sensor/history pipeline, investigate drift and calibrated intervals, and evaluate interventions with appropriate evidence. Any new model development needs a fresh protected evaluation design; none is implemented here. |

Source of exact facts: [schema](../ml/results/feature_schema.json), [splits](../ml/results/split_metadata.json), [tuning](../ml/results/phase10_tuning_summary.json), [selection lock](../ml/results/phase11_selection_lock.json), [final evaluation](../ml/results/phase11_final_test_evaluation.json), [importance](../ml/results/phase12_feature_importance.json), [model metadata](../ml/results/final_model_metadata.json), [thresholds](../ml/results/phase14_recommendation_thresholds.json). Complete locked parameters remain in methodology/metadata; no new numerical experiment is reported here.

## Final full-stack defense questions

| Question | Actual implementation |
| --- | --- |
| Why a database? | Accounts, ownership, observations, sessions and prediction/recommendation evidence must survive refresh/restart and be isolated per user. |
| Why SQLite locally? | A serverless relational DB supports a reproducible local defense with constraints/transactions; write serialization limits scale. |
| Why PostgreSQL-compatible architecture? | SQLAlchemy types/constraints and Alembic reduce storage coupling. No bundled PostgreSQL driver or live production/concurrency validation is claimed. |
| Password storage? | Salted Argon2id via pwdlib; no plaintext/password hash in public responses. Bootstrap uses hidden confirmation prompts. |
| Why opaque sessions rather than localStorage identity? | Random cookie tokens are HttpOnly, revocable and checked against hashed server-side records, expiry and active user. Client role values are not evidence. |
| How is CSRF handled? | Private mutations require X-SmartEnergy-CSRF: 1 plus trusted Origin validation when supplied. Exact-origin credentialed CORS and SameSite=Lax complement this; the header is not a secret per-session nonce. |
| Ownership enforcement? | Every ordinary resource query is scoped to authenticated owner, returning404 for foreign objects. Role checks guard dedicated admin APIs. |
| Can ADMIN use normal APIs across owners? | No. Dedicated admin inspection/status APIs allow oversight; ordinary building/measurement/forecast APIs remain owner-only. |
| Why atomic CSV? | Parse/validate before persistence, one transaction, no silent skipping. Duplicate/conflicting/invalid input rejects the import; late DB failures roll back. |
| Why exactly 1,009 measurements? | The origin itself plus origin-relative t-1008 seven-day lag requires 1,009 continuous ten-minute points; raw count alone cannot prove this. |
| How are 42 features created? |26 raw numeric observations plus existing temporal/cyclical/lag/rolling formulas; production uses the shared finalized research definitions/order, no future observations or client-computed substitutes. |
| How are stale forecasts prevented? | Dashboard compares latest origin, current model checksum and exact feature fingerprint. Older/corrected-context predictions remain historical until explicit matching prediction exists. |
| What is the fingerprint? | SHA-256 of canonical ordered feature names/finite float64 values. Together with building/source/model it identifies semantic input; it is not a confidence score. |
| How is history persisted? | Predictions store Wh/horizon/model/source/checksum, canonical input snapshot/hash and recommendation snapshot in one transaction. Identical input reuses a row; corrected inputs may create distinct history. |
| What happens on deactivation? | Dedicated guarded status change revokes all sessions while retaining buildings/history. Next protected request/login fails. Reactivation requires fresh login and never revives old tokens. In-flight authorized work may finish. |
| Why not validated for arbitrary buildings? | Schema compatibility and ownership supply no independent external-building evidence. Original TEST is later-period data from one reference building; transfer is experimental. |
| Main security limits? | No MFA/rate limiting/email recovery delivery/central audit or production certification; HTTPS/headers/proxy limits require deployment policy; SQLite/live PostgreSQL concurrency limits remain. |

The local application's naive observation clock is distinct from naive-UTC audit timestamps. There is no inferred timezone/DST conversion, background prediction scheduler, occupancy source or automatic actuator integration.
