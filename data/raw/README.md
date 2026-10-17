# Raw dataset

Place the UCI Appliances Energy Prediction dataset in this directory when the
data-ingestion phase is authorized. Keep the original downloaded data unchanged;
cleaned outputs belong in `data/processed/` at the project root.

The planned prediction target is `Appliances`, with observations at 10-minute
intervals. Verify the source schema, units, and timestamps before analysis.

Raw data is not committed to Git. The root `.gitignore` excludes local data in
this directory while allowing README files and `.gitkeep` placeholders. Do not
force-add dataset files. Record the source, retrieval date, and checksum during
the data-ingestion phase so the analysis can be reproduced.

Phase 1 only creates this location; it does not download or generate a dataset.
