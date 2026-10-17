# Raw dataset

The local `energydata_complete.csv` is the UCI Appliances Energy Prediction
dataset specified for this project. The file is kept unchanged; cleaned outputs,
if authorized later, belong in `data/processed/`.

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

Variable grouping follows the conventional UCI dataset descriptions; detailed
sensor locations and measurement units are not established by metadata stored
in this repository. `Press_mm_hg` indicates mm Hg in its name. Units for all
other measurements, including `Appliances` and `lights`, require verification
from authoritative source metadata. No columns have been removed or altered.
