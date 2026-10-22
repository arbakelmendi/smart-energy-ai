"""Real UCI DB/research parity and unchanged Phase5 export, no model invocation."""
from pathlib import Path
import csv, hashlib, json, os, secrets, sys, tempfile
from unittest.mock import patch
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def verify():
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import func, select
    from sqlalchemy.orm import Session
    from backend.database import create_database_engine
    from backend.db_models import User, Measurement, Prediction, RAW_MEASUREMENT_COLUMNS
    from backend.prediction_features import assess_prediction_readiness, REQUIRED_OBSERVATIONS, ordered_feature_names
    from scripts.import_uci_reference_building import import_reference
    from ml.src.feature_engineering import (engineer_dataset, engineer_origin_features, sha256_file,
        TEMPORAL_FEATURES, CYCLICAL_FEATURES, LAG_FEATURES, ROLLING_WINDOWS)
    from datetime import datetime
    names=list(ordered_feature_names())
    source_hash=sha256_file(ROOT/'data/raw/energydata_complete.csv')
    artifact_hash=sha256_file(ROOT/'data/processed/energydata_features.csv')
    with tempfile.TemporaryDirectory(prefix='phase25-parity-') as directory:
        # The unchanged supervised workflow exports only to disposable output, never historical artifacts.
        output=Path(directory)/'features.csv'
        regenerated, report=engineer_dataset(output_path=output)
        assert sha256_file(output)==artifact_hash,'Research CSV changed after extracting shared formulas'
        url='sqlite:///'+(Path(directory)/'parity.db').as_posix()
        with patch.dict(os.environ,{'DATABASE_URL':url}):
            command.upgrade(Config(str(ROOT/'alembic.ini')),'head')
        engine=create_database_engine(url)
        try:
            with Session(engine) as db:
                # No login in this local utility; isolated test identity never leaves temporary DB.
                email='parity-'+secrets.token_hex(8)+'@example.com'
                db.add(User(email=email,full_name='Parity reference admin',password_hash='test-only-no-login',role='ADMIN'));db.commit()
                result=import_reference(db,email)
                bid=result['building_id']
                with (ROOT/'data/raw/energydata_complete.csv').open(newline='',encoding='utf-8') as stream:
                    raw=list(csv.DictReader(stream))
                first=datetime.fromisoformat(raw[REQUIRED_OBSERVATIONS-1]['date'])
                assert regenerated.iloc[0]['date'].to_pydatetime()==first
                # First ready, middle TRAIN and later VALIDATION; no test metrics or model calls.
                selected=[regenerated.iloc[0],regenerated.iloc[6000],regenerated.iloc[15000]]
                comparisons=[]
                for expected in selected:
                    stamp=expected['date'].to_pydatetime()
                    assessed=assess_prediction_readiness(db,bid,as_of=stamp)
                    assert assessed.readiness.ready,assessed.readiness
                    assert assessed.feature_row.feature_timestamp==stamp
                    frame=assessed.feature_row.as_frame()
                    assert frame.columns.tolist()==names
                    actual=frame.iloc[0].to_numpy(dtype=float)
                    reference=expected[names].to_numpy(dtype=float)
                    differences=np.abs(actual-reference)
                    exact_names = ['Appliances', 'lights', *TEMPORAL_FEATURES, *CYCLICAL_FEATURES, *LAG_FEATURES,
                        *(f'appliances_roll_mean_{period}' for period in ROLLING_WINDOWS)]
                    exact_indices = [names.index(name) for name in exact_names]
                    np.testing.assert_array_equal(actual[exact_indices], reference[exact_indices])
                    # Absolute tolerance only: float64 parser/serialization and rolling update rounding.
                    np.testing.assert_allclose(actual,reference,rtol=0,atol=1e-10)
                    comparisons.append({'timestamp':stamp.isoformat(),'features_compared':len(names),
                        'max_absolute_difference':float(differences.max()),'mismatches_above_tolerance':0,
                        'exactly_enforced_features':exact_names,'features_exactly_equal':int((differences==0).sum()),
                        'differing_features':[names[i] for i,d in enumerate(differences) if d!=0]})
                # Latest raw row has no observed next-step target; readiness must still work.
                latest=assess_prediction_readiness(db,bid)
                assert latest.readiness.ready
                assert latest.feature_row.feature_timestamp==datetime.fromisoformat(raw[-1]['date'])
                # Independent full-prefix shared transform confirms the last available inference row,
                # without reading held-out labels or running a model.
                raw_frame=pd.DataFrame([{**{f:float(row[f]) for f in RAW_MEASUREMENT_COLUMNS},
                    'date':datetime.fromisoformat(row['date'])} for row in raw])
                full_latest=engineer_origin_features(raw_frame).loc[:,names].iloc[-1].to_numpy(dtype=float)
                latest_delta=float(np.abs(latest.feature_row.as_frame().iloc[0].to_numpy()-full_latest).max())
                np.testing.assert_allclose(latest.feature_row.as_frame().iloc[0],full_latest,rtol=0,atol=1e-10)
                assert db.scalar(select(func.count(Prediction.id)))==0
                total=db.scalar(select(func.count(Measurement.id)))
        finally:engine.dispose()
    assert sha256_file(ROOT/'data/raw/energydata_complete.csv')==source_hash
    assert sha256_file(ROOT/'data/processed/energydata_features.csv')==artifact_hash
    return {'passed':True,'source_rows_imported':total,'feature_count':len(names),'feature_order':names,
        'first_inference_ready_timestamp':first.isoformat(),'minimum_observations':REQUIRED_OBSERVATIONS,
        'parity_points':comparisons,'absolute_tolerance':1e-10,'relative_tolerance':0,
        'tolerance_reason':'Float64 CSV parsing/serialization and pandas rolling reduction initialization on bounded versus full prefixes; no feature approximation',
        'maximum_absolute_difference':max(c['max_absolute_difference'] for c in comparisons),
        'full_UCI_latest_ready':True,'latest_without_future_target':latest.feature_row.feature_timestamp.isoformat(),
        'latest_prefix_rolling_max_difference':latest_delta,'research_export_byte_identical':True,
        'research_export_sha256':artifact_hash,'alignment_checks_passed':all(report['alignment_checks'].values()),
        'source_sha256_unchanged':source_hash,'no_model_loaded_or_predictions_created':True,'temporary_database_removed':True}


if __name__=='__main__':
    result=verify()
    (ROOT/'ml/results/generated/phase25_feature_parity.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
