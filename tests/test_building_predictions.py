"""Real TRAIN-history forecasts and fingerprint-aware persistence in isolated DBs."""
import csv,json,secrets,unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import threading
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import insert,select,func,text
from sqlalchemy.exc import OperationalError,IntegrityError
import test_buildings as fixtures
from backend.db_models import Measurement,Prediction,RAW_MEASUREMENT_COLUMNS
from backend import services
from backend.prediction_features import assess_prediction_readiness
from backend.building_prediction_service import feature_snapshot

class BuildingPredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.BuildingTests.setUpClass.__func__(cls)
        with (fixtures.ROOT/'data/raw/energydata_complete.csv').open(newline='',encoding='utf-8') as stream:
            reader=csv.DictReader(stream);raw=[next(reader) for _ in range(1011)]
        from datetime import datetime
        cls.observations=[{'timestamp':datetime.fromisoformat(r['date']),**{f:float(r[f]) for f in RAW_MEASUREMENT_COLUMNS}} for r in raw]
    def setUp(self):
        fixtures.BuildingTests.setUp(self);services.model_bundle.cache_clear();services.thresholds.cache_clear()
    def tearDown(self):
        services.model_bundle.cache_clear();services.thresholds.cache_clear();fixtures.BuildingTests.tearDown(self)
    create=fixtures.BuildingTests.create
    def path(self):
        if not hasattr(self,'bid'):self.bid=self.create()['id']
        return f'/buildings/{self.bid}/predictions'
    def seed(self,n=1009):
        self.path()
        with self.factory() as db:db.execute(insert(Measurement),[{'building_id':self.bid,**r} for r in self.observations[:n]]);db.commit()
    def predict(self):return self.a.post(self.path())
    def count(self):
        with self.factory() as db:return db.scalar(select(func.count(Prediction.id)))
    def test_real_own_prediction_persisted_and_helper_parity(self):
        self.seed();result=self.predict();self.assertEqual(result.status_code,200,result.text);body=result.json()
        with self.factory() as db:
            feature=assess_prediction_readiness(db,self.bid).feature_row;row=db.get(Prediction,body['id'])
            direct=services.inference.predict_next_appliances(feature.as_frame(),services.model_bundle()).iloc[0]
            rec=services.recommendations.predict_and_recommend(feature.as_frame(),model_bundle=services.model_bundle(),thresholds=services.thresholds())[0]
            self.assertEqual(body['prediction_wh'],float(direct));self.assertEqual(row.prediction_wh,float(direct))
            self.assertEqual(body['recommendation'],{'level':rec['prediction']['level'],'code':rec['recommendation']['code'],'priority':rec['recommendation']['priority'],'text':rec['recommendation']['message']})
            self.assertEqual(row.recommendation_text,rec['recommendation']['message']);self.assertEqual(row.feature_hash,feature_snapshot(feature)[1])
            snapshot=json.loads(row.feature_snapshot_json);self.assertEqual(snapshot['feature_names'],list(feature.feature_names));self.assertEqual(snapshot['feature_values'],list(feature.values))
        self.assertEqual(body['source_timestamp'],self.observations[1008]['timestamp'].isoformat())
        self.assertEqual(body['forecast_timestamp'],(self.observations[1008]['timestamp']+timedelta(minutes=10)).isoformat())
        self.assertEqual(body['unit'],'Wh');self.assertEqual(body['horizon_minutes'],10)
        self.assertEqual(body['model_checksum'],services.model_bundle()[1]['model_artifact_sha256']);self.assertTrue(body['matches_current_history'])
        self.assertIn('experimental',body['validation_notice']);self.assertEqual(body['current_appliances_wh'],self.observations[1008]['Appliances'])
        for forbidden in ['confidence','savings','features','password','email','token','automatic_control']:
            self.assertNotIn(forbidden,body)
    def test_authentication_and_other_owner_admin_denied(self):
        self.seed()
        for client in [self.b,self.admin]:
            self.assertEqual(client.post(self.path()).status_code,404);self.assertEqual(client.get(self.path()).status_code,404)
        with TestClient(fixtures.app,base_url='http://localhost',headers={'X-SmartEnergy-CSRF':'1'}) as anonymous:
            self.assertEqual(anonymous.post(self.path()).status_code,401);self.assertEqual(anonymous.get(self.path()).status_code,401)
        self.assertEqual(self.count(),0)
    def test_admin_own_forecast(self):
        self.bid=self.create(self.admin)['id'];self.seed();self.assertEqual(self.admin.post(self.path()).status_code,200)
        self.assertEqual(self.a.get(self.path()).status_code,404)
    def test_not_ready_never_loads_model_or_persists(self):
        self.seed(1008)
        with patch('backend.services.model_bundle',side_effect=AssertionError('No model')):
            result=self.predict()
        self.assertEqual(result.status_code,409);self.assertEqual(result.json()['detail']['reason_code'],'INSUFFICIENT_HISTORY');self.assertEqual(self.count(),0)
    def test_server_reassesses_stale_ready_after_delete(self):
        self.seed();self.assertTrue(self.a.get(f'/buildings/{self.bid}/prediction-readiness').json()['ready'])
        with self.factory() as db:row=db.scalar(select(Measurement).where(Measurement.building_id==self.bid,Measurement.timestamp==self.observations[500]['timestamp']));db.delete(row);db.commit()
        with patch('backend.services.model_bundle',side_effect=AssertionError('No model')):result=self.predict()
        self.assertEqual(result.status_code,409);self.assertEqual(self.count(),0)
    def test_repeated_request_reuses_and_only_one_inference_load(self):
        self.seed()
        load=services.inference.load_final_model;predict=services.recommendations.predict_and_recommend
        with patch('backend.services.inference.load_final_model',wraps=load) as loads,patch('backend.services.recommendations.predict_and_recommend',wraps=predict) as calls:
            first=self.predict().json();again=self.predict().json()
            self.assertEqual(first['id'],again['id']);self.assertFalse(first['reused_existing_prediction']);self.assertTrue(again['reused_existing_prediction'])
            self.assertEqual(loads.call_count,1);self.assertEqual(calls.call_count,1)
        self.assertEqual(self.count(),1)
    def test_new_latest_preserves_old_prediction_and_history_order(self):
        self.seed();first=self.predict().json()
        with self.factory() as db:db.add(Measurement(building_id=self.bid,**self.observations[1009]));db.commit()
        before=self.a.get(self.path()).json();self.assertFalse(before['items'][0]['matches_current_history'])
        second=self.predict().json();self.assertNotEqual(first['id'],second['id']);self.assertEqual(self.count(),2)
        items=self.a.get(self.path()).json()['items'];self.assertEqual([r['id'] for r in items],[second['id'],first['id']]);self.assertTrue(items[0]['matches_current_history']);self.assertFalse(items[1]['matches_current_history'])
    def test_historical_change_same_source_changes_fingerprint_preserves_versions(self):
        self.seed();first=self.predict().json()
        with self.factory() as db:row=db.scalar(select(Measurement).where(Measurement.building_id==self.bid,Measurement.timestamp==self.observations[1007]['timestamp']));row.Appliances+=10;db.commit()
        self.assertFalse(self.a.get(self.path()).json()['items'][0]['matches_current_history'])
        second=self.predict().json();self.assertEqual(second['source_timestamp'],first['source_timestamp']);self.assertNotEqual(second['feature_hash'],first['feature_hash']);self.assertNotEqual(second['id'],first['id']);self.assertEqual(self.count(),2)
        with self.factory() as db:row=db.scalar(select(Measurement).where(Measurement.building_id==self.bid,Measurement.timestamp==self.observations[1007]['timestamp']));row.Appliances-=10;db.commit()
        self.assertEqual(self.predict().json()['id'],first['id']);self.assertEqual(self.count(),2)
    def test_irrelevant_old_insert_no_new_forecast(self):
        self.seed();first=self.predict().json()
        old={**self.observations[0],'timestamp':self.observations[0]['timestamp']-timedelta(days=30)}
        with self.factory() as db:db.add(Measurement(building_id=self.bid,**old));db.commit()
        self.assertEqual(self.predict().json()['id'],first['id']);self.assertEqual(self.count(),1)
    def test_history_pagination_order_and_empty(self):
        self.assertEqual(self.a.get(self.path()).json()['items'],[])
        self.seed();first=self.predict().json()
        with self.factory() as db:db.add(Measurement(building_id=self.bid,**self.observations[1009]));db.commit()
        self.predict();page=self.a.get(self.path()+'?limit=1&offset=1').json();self.assertEqual(page['total'],2);self.assertEqual(page['items'][0]['id'],first['id'])
        for query in ['limit=0','limit=501','offset=-1']:self.assertEqual(self.a.get(self.path()+'?'+query).status_code,422)
    def test_no_feature_or_owner_request_body_and_csrf(self):
        self.seed()
        for body in [{'features':{}},{'owner_id':self.ids['b']},{'source_timestamp':'2024-01-01'}]:self.assertEqual(self.a.post(self.path(),json=body).status_code,422)
        self.assertEqual(self.a.post(self.path(),headers={'X-SmartEnergy-CSRF':''}).status_code,403)
        self.assertEqual(self.a.post(self.path(),headers={'Origin':'https://untrusted.invalid'}).status_code,403)
        self.assertEqual(self.a.post(self.path(),json={}).status_code,200)
        self.assertEqual(self.a.get(self.path()).headers['cache-control'],'no-store')
    def test_missing_model_safe_and_history_independent(self):
        self.seed()
        with patch('ml.src.model_inference.ARTIFACT_PATH',Path(self.directory.name)/'missing-model.json'):
            self.assertEqual(self.predict().status_code,503)
        self.assertEqual(self.count(),0)
        self.predict();services.model_bundle.cache_clear()
        with patch('backend.services.model_bundle',side_effect=AssertionError('History must not load model')):
            result=self.a.get(self.path());self.assertEqual(result.status_code,200);self.assertEqual(result.json()['total'],1)
    def test_nonfinite_or_negative_model_output_not_persisted(self):
        self.seed()
        for value in [float('nan'),float('inf'),-1.0]:
            with patch('backend.services.inference.predict_next_appliances',return_value=pd.Series([value])):
                self.assertEqual(self.predict().status_code,503);self.assertEqual(self.count(),0)
    def test_recommendation_or_model_failure_safe(self):
        self.seed()
        for target in ['backend.services.recommendations.predict_and_recommend','backend.services.inference.predict_next_appliances']:
            with patch(target,side_effect=RuntimeError('private-internal-details')):
                result=self.predict();self.assertEqual(result.status_code,503);self.assertNotIn('private-internal-details',result.text);self.assertEqual(self.count(),0)
    def test_threshold_unavailable(self):
        self.seed()
        with patch('backend.services.thresholds',side_effect=services.ResourceUnavailable('Threshold resource unavailable')):self.assertEqual(self.predict().status_code,503)
        self.assertEqual(self.count(),0)
    def test_negative_current_retains_existing_recommendation_policy(self):
        self.seed()
        with self.factory() as db:row=db.scalar(select(Measurement).order_by(Measurement.timestamp.desc()));row.Appliances=-1;db.commit()
        self.assertEqual(self.predict().status_code,422);self.assertEqual(self.count(),0)
    def test_commit_failure_rolls_back_snapshot(self):
        self.seed()
        from sqlalchemy.orm import Session
        with patch.object(Session,'commit',side_effect=OperationalError('test-only',{},None)):
            result=self.predict();self.assertEqual(result.status_code,503)
        self.assertEqual(self.count(),0)
    def test_history_change_during_inference_rejected(self):
        self.seed();original=services.recommendations.predict_and_recommend
        def changed(*args,**kwargs):
            result=original(*args,**kwargs)
            with self.factory() as db:row=db.scalar(select(Measurement).where(Measurement.building_id==self.bid,Measurement.timestamp==self.observations[-3]['timestamp']));row.Appliances+=1;db.commit()
            return result
        with patch('backend.services.recommendations.predict_and_recommend',side_effect=changed):result=self.predict()
        self.assertEqual(result.status_code,409);self.assertEqual(result.json()['detail']['reason_code'],'HISTORY_CHANGED');self.assertEqual(self.count(),0)
    def test_database_unique_input_and_snapshot_pair_constraint(self):
        self.seed();created=self.predict().json()
        with self.factory() as db:
            row=db.get(Prediction,created['id']);duplicate=Prediction(building_id=self.bid,source_timestamp=row.source_timestamp,prediction_wh=row.prediction_wh,model_name=row.model_name,model_checksum=row.model_checksum,feature_hash=row.feature_hash,feature_snapshot_json=row.feature_snapshot_json)
            db.add(duplicate)
            with self.assertRaises(IntegrityError):db.commit()
            db.rollback()
            db.add(Prediction(building_id=self.bid,source_timestamp=row.source_timestamp,prediction_wh=row.prediction_wh,model_name=row.model_name,model_checksum=row.model_checksum,feature_hash='0'*64))
            with self.assertRaises(IntegrityError):db.commit()
            db.rollback()
    def test_concurrent_same_input_creates_only_one_record(self):
        self.seed();services.model_bundle();barrier=threading.Barrier(2);original=services.recommendations.predict_and_recommend
        def parallel(*args,**kwargs):barrier.wait(timeout=20);return original(*args,**kwargs)
        def send():
            with TestClient(fixtures.app,base_url='http://localhost',cookies=self.a.cookies,headers={'X-SmartEnergy-CSRF':'1'}) as client:return client.post(self.path())
        with patch('backend.services.recommendations.predict_and_recommend',side_effect=parallel):
            with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:send(),range(2)))
        self.assertEqual([r.status_code for r in results],[200,200]);self.assertEqual(results[0].json()['id'],results[1].json()['id']);self.assertEqual(self.count(),1)
    def test_legacy_history_is_not_invented(self):
        self.path()
        with self.factory() as db:db.add(Prediction(building_id=self.bid,source_timestamp=self.observations[0]['timestamp'],prediction_wh=10,model_name='legacy',model_checksum='0'*64));db.commit()
        item=self.a.get(self.path()).json()['items'][0];self.assertIsNone(item['feature_hash']);self.assertIsNone(item['current_appliances_wh']);self.assertIsNone(item['recommendation']);self.assertFalse(item['matches_current_history'])
