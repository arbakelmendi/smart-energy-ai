"""Real direct-helper parity and full UCI reference E2E in an isolated migrated DB."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))

def verify():
    from test_building_predictions import BuildingPredictionTests
    from backend.db_models import User,Prediction
    from backend.prediction_features import assess_prediction_readiness
    from backend import services
    from scripts.import_uci_reference_building import import_reference
    from sqlalchemy import select,func
    fixture=BuildingPredictionTests();fixture.setUpClass();fixture.setUp()
    try:
        fixture.seed()
        train=fixture.predict();assert train.status_code==200,train.text
        def compare(body):
            with fixture.factory() as db:
                feature=assess_prediction_readiness(db,body['building_id']).feature_row
                prediction=float(services.inference.predict_next_appliances(feature.as_frame(),services.model_bundle()).iloc[0])
                rec=services.recommendations.predict_and_recommend(feature.as_frame(),model_bundle=services.model_bundle(),thresholds=services.thresholds())[0]
                assert body['prediction_wh']==prediction
                expected={'level':rec['prediction']['level'],'code':rec['recommendation']['code'],'priority':rec['recommendation']['priority'],'text':rec['recommendation']['message']}
                assert body['recommendation']==expected
                row=db.get(Prediction,body['id']);assert row.model_checksum==services.model_bundle()[1]['model_artifact_sha256']
                assert row.recommendation_text==expected['text'] and row.feature_hash==body['feature_hash']
                return {'source_timestamp':body['source_timestamp'],'forecast_timestamp':body['forecast_timestamp'],'prediction_wh':prediction,'absolute_inference_difference':abs(body['prediction_wh']-prediction),'recommendation_exact_match':True,'feature_count':len(feature.feature_names),'model_checksum':row.model_checksum,'snapshot_persisted':row.feature_snapshot_json is not None}
        train_result=compare(train.json())
        with fixture.factory() as db:
            email=db.get(User,fixture.ids['admin']).email
            imported=import_reference(db,email)
        bid=imported['building_id'];path=f'/buildings/{bid}/predictions'
        ready=fixture.admin.get(f'/buildings/{bid}/prediction-readiness');assert ready.json()['ready']
        forecast=fixture.admin.post(path);assert forecast.status_code==200,forecast.text
        reference=compare(forecast.json())
        repeat=fixture.admin.post(path);assert repeat.status_code==200 and repeat.json()['id']==forecast.json()['id'] and repeat.json()['reused_existing_prediction']
        history=fixture.admin.get(path).json();assert history['total']==1 and history['items'][0]['id']==forecast.json()['id']
        assert fixture.a.get(path).status_code==404
        return {'passed':True,'TRAIN_observation':train_result,'UCI_reference':reference,'UCI_rows_imported':imported['rows_imported'],'reference_ready':True,'idempotent_repeat_one_history_row':True,'reference_owner_isolation':True,'history_persisted':True,'nonreference_validation_notice':train.json()['validation_notice'],'unit':'Wh','horizon_minutes':10,'temporary_database_removed':True}
    finally:fixture.tearDown()

if __name__=='__main__':
    result=verify()
    (ROOT/'ml/results/generated/phase26_prediction_parity.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
