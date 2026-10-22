"""Readiness endpoint/DB integration with migrated isolated data and real sessions."""
import unittest
from unittest.mock import patch
from sqlalchemy import insert,select,func,event
from fastapi.testclient import TestClient
import test_buildings as fixtures
from test_prediction_features import history
from backend.db_models import Measurement,Prediction
from backend.prediction_features import assess_prediction_readiness,get_latest_required_history

class ReadinessTests(unittest.TestCase):
    setUpClass=classmethod(fixtures.BuildingTests.setUpClass.__func__)
    setUp=fixtures.BuildingTests.setUp
    tearDown=fixtures.BuildingTests.tearDown
    create=fixtures.BuildingTests.create
    def path(self):
        if not hasattr(self,'bid'):self.bid=self.create()['id']
        return f'/buildings/{self.bid}/prediction-readiness'
    def seed(self,rows):
        self.path()
        with self.factory() as db:
            db.execute(insert(Measurement),[{'building_id':self.bid,**r} for r in rows]);db.commit()
    def test_empty_api_safe_factual_and_no_store(self):
        r=self.a.get(self.path());self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['reason_code'],'NO_MEASUREMENTS');self.assertEqual(r.json()['measurement_count'],0)
        self.assertEqual(r.json()['required_observations'],1009);self.assertEqual(r.headers['cache-control'],'no-store')
        self.assertNotIn('features',r.json());self.assertNotIn('prediction_wh',r.json())
    def test_owner_policy_user_admin_anonymous(self):
        path=self.path()
        for client in [self.b,self.admin]:self.assertEqual(client.get(path).status_code,404)
        with TestClient(fixtures.app,base_url='http://localhost') as client:self.assertEqual(client.get(path).status_code,401)
        own=self.create(self.admin)['id'];self.assertEqual(self.admin.get(f'/buildings/{own}/prediction-readiness').status_code,200)
    def test_exact_minimum_out_of_order_db_and_bounded_fetch(self):
        self.seed(list(reversed(history(1500))))
        r=self.a.get(self.path()).json();self.assertTrue(r['ready']);self.assertEqual(r['measurement_count'],1500)
        with self.factory() as db:
            rows=get_latest_required_history(db,self.bid);self.assertEqual(len(rows),1010)
            self.assertEqual(rows[-1]['timestamp'],history(1500)[-1]['timestamp'])
            self.assertLess(rows[0]['timestamp'],rows[-1]['timestamp'])
            result=assess_prediction_readiness(db,self.bid)
            self.assertEqual(result.feature_row.ordered_mapping()['Appliances'],history(1500)[-1]['Appliances'])
    def test_delete_breaks_history_and_restore_returns_ready(self):
        rows=history();self.seed(rows);self.assertTrue(self.a.get(self.path()).json()['ready'])
        with self.factory() as db:mid=db.scalar(select(Measurement.id).where(Measurement.building_id==self.bid,Measurement.timestamp==rows[500]['timestamp']))
        self.assertEqual(self.a.delete(f'/buildings/{self.bid}/measurements/{mid}').status_code,204)
        self.assertEqual(self.a.get(self.path()).json()['reason_code'],'LATEST_WINDOW_HAS_GAPS')
        body={**rows[500],'timestamp':rows[500]['timestamp'].isoformat()}
        self.assertEqual(self.a.post(f'/buildings/{self.bid}/measurements',json=body).status_code,201)
        self.assertTrue(self.a.get(self.path()).json()['ready'])
    def test_new_latest_gap_no_older_fallback(self):
        from datetime import timedelta
        rows=history();self.seed(rows)
        extra={**rows[-1],'timestamp':rows[-1]['timestamp']+timedelta(minutes=20)};self.seed([extra])
        r=self.a.get(self.path()).json();self.assertFalse(r['ready']);self.assertEqual(r['continuous_intervals_available'],0)
        self.assertEqual(r['latest_measurement_timestamp'],extra['timestamp'].isoformat())
    def test_as_of_does_not_use_future_rows(self):
        rows=history(1200);self.seed(rows)
        with self.factory() as db:
            result=assess_prediction_readiness(db,self.bid,as_of=rows[1008]['timestamp'])
            self.assertTrue(result.readiness.ready);self.assertEqual(result.feature_row.feature_timestamp,rows[1008]['timestamp'])
            self.assertEqual(result.feature_row.ordered_mapping()['Appliances'],rows[1008]['Appliances'])
            self.assertEqual(result.readiness.measurement_count,1009)
    def test_missing_contract_is_safe503(self):
        from backend.prediction_features import FeatureContractUnavailable
        with patch('backend.prediction_readiness.assess_prediction_readiness',side_effect=FeatureContractUnavailable('private path')):
            r=self.a.get(self.path());self.assertEqual(r.status_code,503);self.assertNotIn('private path',r.text)
    def test_no_model_or_recommendation_or_database_write(self):
        self.seed(history())
        with patch('backend.services.inference.load_final_model',side_effect=AssertionError('no model')),patch('backend.services.inference.predict_next_appliances',side_effect=AssertionError('no predict')),patch('backend.services.recommendations.predict_and_recommend',side_effect=AssertionError('no recommendation')):
            self.assertTrue(self.a.get(self.path()).json()['ready'])
        with self.factory() as db:
            self.assertEqual(db.scalar(select(func.count(Prediction.id))),0)
            self.assertEqual(db.scalar(select(func.count(Measurement.id))),1009)

    def test_corrupt_sqlite_timestamp_fails_safely(self):
        from sqlalchemy import text
        self.seed(history(1))
        with self.factory() as db:
            db.execute(text("UPDATE measurements SET timestamp = 'invalid-date' WHERE building_id=:id"),{'id':self.bid});db.commit()
        result=self.a.get(self.path())
        self.assertEqual(result.status_code,200);self.assertEqual(result.json()['reason_code'],'INVALID_RAW_DATA')
        self.assertFalse(result.json()['ready']);self.assertNotIn('invalid-date',result.text)
    def test_corrupt_sqlite_raw_value_not_filled(self):
        from sqlalchemy import text
        self.seed(history())
        with self.factory() as db:
            db.execute(text('PRAGMA ignore_check_constraints=ON'))
            db.execute(text("UPDATE measurements SET T1 = 'invalid' WHERE building_id=:id"),{'id':self.bid});db.commit()
            db.execute(text('PRAGMA ignore_check_constraints=OFF'))
        result=self.a.get(self.path())
        self.assertEqual(result.status_code,200);self.assertEqual(result.json()['reason_code'],'INVALID_RAW_DATA')
        self.assertFalse(result.json()['ready'])
