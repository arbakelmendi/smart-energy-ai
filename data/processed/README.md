# Processed data

`energydata_cleaned.csv` is generated from the UCI Appliances Energy Prediction raw CSV by `ml/src/preprocess.py`. The pipeline never modifies the raw CSV. It removes only `rv1` and `rv2`, which are identical row by row and are random/questionable rather than physical variables. No observations or target outliers are removed.

`energydata_features.csv` is generated reproducibly from the cleaned CSV by `ml/src/feature_engineering.py` for one-step-ahead prediction at a 10-minute horizon. It retains the current-time `Appliances` input and creates the next-observation target, approved temporal/cyclical features, historical lags through 7 days, and backward-looking rolling statistics.

The first 1,008 rows are excluded because the required 7-day historical context is unavailable; the final row is excluded because its next-step target is unavailable. These are supervised-sample alignment exclusions, not data cleaning. No scaling or train/validation/test split has been applied, and no model has been trained.

Generated CSV files are ignored by Git; do not force-add them.
