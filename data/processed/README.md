# Processed data

`energydata_cleaned.csv` is generated from `data/raw/energydata_complete.csv` (UCI Appliances Energy Prediction) by running `ml/src/preprocess.py`. The pipeline is reproducible and never modifies the raw CSV.

Only `rv1` and `rv2` are removed: they are identical row by row and are random/questionable variables without physical interpretation. No observations or target outliers are removed. No imputation, feature engineering, scaling, or splitting has been performed.

The generated CSV is ignored by Git; do not force-add it.
