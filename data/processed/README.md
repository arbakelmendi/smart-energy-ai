# Processed data

`energydata_cleaned.csv` is generated from the UCI Appliances Energy Prediction raw CSV by `ml/src/preprocess.py`. The pipeline never modifies the raw CSV. It removes only `rv1` and `rv2`, which are identical row by row and are random/questionable rather than physical variables. No observations or target outliers are removed.

`energydata_features.csv` is generated reproducibly from the cleaned CSV by `ml/src/feature_engineering.py` for one-step-ahead prediction at a 10-minute horizon. It retains the current-time `Appliances` input and creates the next-observation target, approved temporal/cyclical features, historical lags through 7 days, and backward-looking rolling statistics.

The first 1,008 rows are excluded because the required 7-day historical context is unavailable; the final row is excluded because its next-step target is unavailable. These are supervised-sample alignment exclusions, not data cleaning.

`energy_train.csv`, `energy_validation.csv`, and `energy_test.csv` are generated reproducibly from the feature dataset by `ml/src/split_data.py` using contiguous chronological 70%/15%/15% partitions. Split boundaries, checksums, and the model feature schema are recorded in `ml/results/split_metadata.json` and `ml/results/feature_schema.json`.

Generated CSV files are ignored by Git; do not force-add them. No scaling or model training has been performed. The test split is reserved for one final evaluation after model selection.
