"""Bounded factual dashboard summaries and shared current-input matching."""
import unittest
from unittest.mock import patch
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import insert,select,func
import test_building_predictions as fixtures
from backend.db_models import Measurement,Prediction

class DashboardTests(unittest.TestCase):
    setUpClass=classmethod(fixtures.BuildingPredictionTests.setUpClass.__func__)
    setUp=fixtures.BuildingPredictionTests.setUp
    tearDown=fixtures.BuildingPredictionTests.tearDown
    create=fixtures.BuildingPredictionTests.create
    path=fixtures.BuildingPredictionTests.path
    seed=fixtures.BuildingPredictionTests.seed
    predict=fixtures.BuildingPredictionTests.predict
    def summary(self,query=''):
        self.path();return self.a.get(f'/buildings/{self.bid}/dashboard-summary'+query)
    def test_empty_counts_null_values_and_no_fake_metrics(self):
        r=self.summary();self.assertEqual(r.status_code,200,r.text);data=r.json()
        self.assertEqual(data['measurement_count'],0);self.assertEqual(data['prediction_count'],0)
        for field in ['latest_measurement','earliest_timestamp','latest_timestamp','current_prediction','latest_stored_prediction']:self.assertIsNone(data[field])
        self.assertEqual(data['energy_history'],[]);self.assertEqual(data['readiness']['reason_code'],'NO_MEASUREMENTS')
        for field in ['savings','confidence','occupancy','cost','efficiency_score']:self.assertNotIn(field,data)
        self.assertEqual(r.headers['cache-control'],'no-store')
    def test_anonymous_user_admin_owner_policy(self):
        self.path();url=f'/buildings/{self.bid}/dashboard-summary'
        for client in [self.b,self.admin]:self.assertEqual(client.get(url).status_code,404)
        with TestClient(fixtures.fixtures.app,base_url='http://localhost') as anonymous:self.assertEqual(anonymous.get(url).status_code,401)
        own=self.create(self.admin)['id'];self.assertEqual(self.admin.get(f'/buildings/{own}/dashboard-summary').status_code,200)
    def test_count_range_latest_zero_and_chronological_window(self):
        self.seed(10)
        with self.factory() as db:
            latest=db.scalar(select(Measurement).order_by(Measurement.timestamp.desc()));latest.Appliances=0;db.commit()
        data=self.summary('?limit=3').json()
        self.assertEqual(data['measurement_count'],10);self.assertEqual(data['latest_measurement']['Appliances'],0)
        self.assertEqual(data['earliest_timestamp'],self.observations[0]['timestamp'].isoformat())
        self.assertEqual(data['latest_timestamp'],self.observations[9]['timestamp'].isoformat())
        self.assertEqual([row['timestamp'] for row in data['energy_history']],[row['timestamp'].isoformat() for row in self.observations[7:10]])
        self.assertEqual(data['window_limit'],3)
    def test_bounds_and_default(self):
        self.seed(1009);data=self.summary().json();self.assertEqual(len(data['energy_history']),144)
        self.assertEqual(len(self.summary('?limit=500').json()['energy_history']),500)
        for query in ['?limit=0','?limit=501','?limit=abc']:self.assertEqual(self.summary(query).status_code,422)
    def test_gap_is_preserved_without_synthesized_records(self):
        self.seed(10)
        with self.factory() as db:row=db.scalar(select(Measurement).where(Measurement.timestamp==self.observations[5]['timestamp']));db.delete(row);db.commit()
        data=self.summary().json();self.assertEqual(len(data['energy_history']),9);self.assertEqual(data['readiness']['reason_code'],'LATEST_WINDOW_HAS_GAPS')
        self.assertNotIn(self.observations[5]['timestamp'].isoformat(),[row['timestamp'] for row in data['energy_history']])
    def test_current_prediction_and_new_latest_staleness(self):
        self.seed();first=self.predict().json();data=self.summary().json()
        self.assertEqual(data['current_prediction']['id'],first['id']);self.assertEqual(data['current_prediction']['recommendation'],first['recommendation'])
        with self.factory() as db:db.add(Measurement(building_id=self.bid,**self.observations[1009]));db.commit()
        data=self.summary().json();self.assertIsNone(data['current_prediction']);self.assertEqual(data['latest_stored_prediction']['id'],first['id']);self.assertFalse(data['recent_predictions'][0]['matches_current_history'])
        second=self.predict().json();self.assertEqual(self.summary().json()['current_prediction']['id'],second['id'])
    def test_historical_correction_and_restored_old_version_current(self):
        self.seed();original=self.predict().json()
        # More than the recent-preview limit; matching current result can be an older record.
        for n in range(6):
            with self.factory() as db:
                row=db.scalar(select(Measurement).where(Measurement.timestamp==self.observations[1007]['timestamp']));row.Appliances=self.observations[1007]['Appliances']+n+1;db.commit()
            self.predict()
        with self.factory() as db:
            row=db.scalar(select(Measurement).where(Measurement.timestamp==self.observations[1007]['timestamp']));row.Appliances=self.observations[1007]['Appliances'];db.commit()
        data=self.summary().json();self.assertEqual(data['prediction_count'],7);self.assertEqual(len(data['recent_predictions']),5)
        self.assertEqual(data['current_prediction']['id'],original['id']);self.assertNotEqual(data['latest_stored_prediction']['id'],original['id'])
        self.assertNotIn(original['id'],[r['id'] for r in data['recent_predictions']])
    def test_multiple_buildings_scoped(self):
        self.seed(10);other=self.create()['id']
        with self.factory() as db:db.add(Measurement(building_id=other,**self.observations[0]));db.commit()
        self.assertEqual(self.summary().json()['measurement_count'],10)
        self.assertEqual(self.a.get(f'/buildings/{other}/dashboard-summary').json()['measurement_count'],1)
    def test_summary_no_model_execution_or_writes(self):
        self.seed();self.predict()
        with patch('backend.services.model_bundle',side_effect=AssertionError('No model load')),patch('backend.services.recommendations.predict_and_recommend',side_effect=AssertionError('No forecast')):
            self.assertEqual(self.summary().status_code,200)
        with self.factory() as db:self.assertEqual(db.scalar(select(func.count(Prediction.id))),1)
    def test_building_metadata_updates_and_delete(self):
        self.path();self.a.patch(f'/buildings/{self.bid}',json={'name':'Edited summary building'})
        self.assertEqual(self.summary().json()['building']['name'],'Edited summary building')
        self.a.delete(f'/buildings/{self.bid}');self.assertEqual(self.summary().status_code,404)
    def test_contract_failure_is_controlled(self):
        from backend.prediction_features import FeatureContractUnavailable
        with patch('backend.dashboard.assess_prediction_readiness',side_effect=FeatureContractUnavailable('private-path')):
            result=self.summary();self.assertEqual(result.status_code,503);self.assertNotIn('private-path',result.text)
