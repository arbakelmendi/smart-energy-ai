# Final forecasting model

Generate or verify deterministic regeneration from the project root:

```powershell
.venv\Scripts\python.exe ml/src/save_final_model.py
```

The canonical artifact is `ml/models/final_xgboost_model.json`, produced by XGBoost native `save_model` serialization. JSON is explicitly supported; the .json extension selects it. Existing ignore rules keep this trained model local. Do not force-add it or weaken the ignore rules. Trackable metadata is `ml/results/final_model_metadata.json`; the verification record is `ml/results/phase13_model_persistence.json`. No volatile training timestamp is included.

The fixed Phase 11 Tuned XGBoost configuration is fitted on TRAIN + VALIDATION (15,917 rows) only. TEST is excluded from fitting and accessed solely for the Phase 11 reproduction gate. The Phase 11 held-out metrics remain authoritative. No tuning or feature selection occurs.

The inference input is an already-engineered pandas DataFrame containing exactly the 42 ordered features from `ml/results/feature_schema.json`. The target is `target_appliances_next`: Appliances energy in Wh ten minutes after forecast origin. Date and target are excluded from X; current Appliances is retained. Missing, additional, duplicate or reordered columns and nonnumeric/nonfinite values fail. No raw-data feature engineering, fabricated history, clipping or intervals occur.

```python
from ml.src.model_inference import load_final_model, predict_next_appliances

bundle = load_final_model()  # loads once; verifies artifact checksum and contract
forecasts_wh = predict_next_appliances(engineered_feature_frame, bundle)
```

Inference uses the local model, metadata, schema and Phase 11 selection lock; it does not read datasets. Use the recorded XGBoost version. Deterministic regeneration additionally requires the recorded Python/dependencies, unchanged development splits and Phase 10-12 artifacts. The script builds a temporary candidate, verifies exact reload predictions on the first 128 TRAIN rows, and refuses to replace any differing existing output. Identical outputs are retained; absent outputs are regenerated at the single canonical path. Temporary candidates are cleaned automatically.

Run the new tests after generation:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_model_*.py" -v
```

Artifact integration tests skip when the ignored model is absent; feature-contract unit tests remain available without local datasets. This package prepares later backend inference only. Correct feature timing, units and historical availability remain the caller's responsibility.

Native serialization reference: https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html
