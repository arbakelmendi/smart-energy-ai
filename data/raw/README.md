# Raw dataset

The local `energydata_complete.csv` is the UCI Appliances Energy Prediction
dataset specified for this project. The file is kept unchanged; the completed pipeline writes cleaned outputs to `data/processed/`. Download/place this ignored CSV separately.

## Provenance and integrity

 Official source: UCI Appliances Energy Prediction dataset, DOI: `10.24432/C5VC8G` (retrieval URL/version not recorded locally).
## Units

| Variables | Unit |
| --- | --- |
| `Appliances`, `lights` | Wh |
| `T1`-`T9`, `T_out`, `Tdewpoint` | °C |
| `RH_1`-`RH_9`, `RH_out` | % |
| `Press_mm_hg` | mm Hg |
| `Windspeed` | m/s |
| `Visibility` | km |
| `rv1`, `rv2` | Nondimensional random variables |

No columns have been removed or altered.

## Available variables

| Group | Variables |
| --- | --- |
| Target | `Appliances` |
| Indoor temperature | `T1`-`T5`, `T7`-`T9` |
| Indoor relative humidity | `RH_1`-`RH_5`, `RH_7`-`RH_9` |
| Outdoor/weather | `T6`, `RH_6`, `T_out`, `Press_mm_hg`, `RH_out`, `Windspeed`, `Visibility`, `Tdewpoint` |
| Lighting | `lights` |
| Temporal | `date` |
| Intentionally random/questionable | `rv1`, `rv2` |

The finalized model contract uses Appliances energy in Wh at a ten-minute horizon. `T6`/`RH_6` belong to outdoor/weather context; `lights` is not occupancy. The table above records project units; detailed sensor-location metadata is not reproduced here.

Recorded [inspection](../../ml/notebooks/01_data_exploration.ipynb) and [EDA](../../ml/notebooks/02_exploratory_data_analysis.ipynb) show 19,735 raw rows and 29 columns, 2016-01-11 17:00:00 through 2016-05-27 18:00:00, exact ten-minute spacing, and no missing values, duplicate rows or duplicate timestamps. Raw data remains unchanged; processed outputs remove only `rv1`/`rv2`. This single-building January-May collection does not supply a reliable occupancy input for the model.

Dataset reference: UCI Machine Learning Repository, *Appliances Energy Prediction*, DOI [10.24432/C5VC8G](https://doi.org/10.24432/C5VC8G). Retrieval date/version was not recorded locally. See [methodology](../../docs/research-methodology.md) and [reproduction](../../docs/reproducibility.md); do not force-add the raw CSV.
