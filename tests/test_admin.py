"""Dedicated administrator APIs against migrated disposable SQLite and real sessions."""
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import func, select
import test_building_predictions as fixtures
from backend.db_models import AuthSession, Building, Measurement, Prediction, User
from backend import admin_service
from backend.main import app

class AdminTests(unittest.TestCase):
    setUpClass=classmethod(fixtures.BuildingPredictionTests.setUpClass.__func__)
    setUp=fixtures.BuildingPredictionTests.setUp
    tearDown=fixtures.BuildingPredictionTests.tearDown
    create=fixtures.BuildingPredictionTests.create
    seed=fixtures.BuildingPredictionTests.seed
    path=fixtures.BuildingPredictionTests.path
    predict=fixtures.BuildingPredictionTests.predict

    def status(self, key, value):
        return self.admin.patch(f'/admin/users/{self.ids[key]}/status', json={'is_active':value})

    def test_all_endpoints_authenticate_and_authorize(self):
        paths=['/admin/overview','/admin/users',f'/admin/users/{self.ids["a"]}',
               '/admin/buildings','/admin/buildings/1','/admin/predictions']
        with TestClient(app,base_url='http://localhost',headers={'X-SmartEnergy-CSRF':'1'}) as anon:
            for path in paths:
                self.assertEqual(anon.get(path).status_code,401)
                self.assertEqual(self.a.get(path).status_code,403)
            path=f'/admin/users/{self.ids["b"]}/status'
            self.assertEqual(anon.patch(path,json={'is_active':False}).status_code,401)
            self.assertEqual(self.a.patch(path,json={'is_active':False}).status_code,403)

    def test_overview_exact_persisted_counts_and_no_model(self):
        self.seed(10);self.create(self.b)
        with patch('backend.services.model_bundle',side_effect=AssertionError('No model')):
            r=self.admin.get('/admin/overview')
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json(),dict(total_users=3,active_users=3,inactive_users=0,admin_users=1,
            regular_users=2,total_buildings=2,total_measurements=10,total_predictions=0))
        self.assertEqual(r.headers['cache-control'],'no-store')

    def test_user_pagination_filter_search_and_safe_serialization(self):
        self.create();self.create()
        first=self.admin.get('/admin/users?limit=1').json();second=self.admin.get('/admin/users?limit=1&offset=1').json()
        self.assertEqual(first['total'],3);self.assertNotEqual(first['items'][0]['id'],second['items'][0]['id'])
        self.assertEqual(first['items'][0]['building_count'],2)
        for url,n in [('/admin/users?role=ADMIN',1),('/admin/users?is_active=false',0),('/admin/users?search=%20Isolated%20%20a%20',2),('/admin/users?search=%25',0)]:
            # "Isolated a" also matches administrator; literal percent matches none.
            self.assertEqual(self.admin.get(url).json()['total'],n,url)
        r=self.admin.get('/admin/users?role=USER&search=Isolated%20a').json();self.assertEqual(r['total'],1)
        self.assertEqual(set(first['items'][0]),{'id','email','full_name','role','is_active','created_at','updated_at','building_count'})

    def test_user_detail_counts_and_owned_building_filter(self):
        self.seed(10);self.create(self.b)
        data=self.admin.get(f'/admin/users/{self.ids["a"]}').json()
        self.assertEqual((data['building_count'],data['measurement_count'],data['prediction_count']),(1,10,0))
        r=self.admin.get(f'/admin/buildings?owner_id={self.ids["a"]}').json()
        self.assertEqual(r['total'],1);self.assertEqual(r['items'][0]['owner']['id'],self.ids['a'])

    def test_deactivate_revokes_all_sessions_login_blocked_reactivate_does_not_restore_old_cookie(self):
        self.seed();self.predict()
        with self.factory() as db:
            email=db.get(User,self.ids['a']).email
            before=[db.scalar(select(func.count()).select_from(m)) for m in [Building,Measurement,Prediction]]
        another=TestClient(app,base_url='http://localhost',headers={'X-SmartEnergy-CSRF':'1'});self.clients.append(another)
        self.assertEqual(another.post('/auth/login',json={'email':email,'password':self.password}).status_code,200)
        self.assertFalse(self.status('a',False).json()['is_active'])
        with self.factory() as db:
            self.assertEqual(db.scalar(select(func.count(AuthSession.id)).where(AuthSession.user_id==self.ids['a'])),0)
            self.assertEqual(before,[db.scalar(select(func.count()).select_from(m)) for m in [Building,Measurement,Prediction]])
        for client in [self.a,another]:self.assertEqual(client.get('/auth/me').status_code,401)
        self.assertEqual(self.a.post('/auth/login',json={'email':email,'password':self.password}).status_code,401)
        self.assertTrue(self.status('a',True).json()['is_active'])
        self.assertEqual(another.get('/auth/me').status_code,401)
        self.assertEqual(self.a.post('/auth/login',json={'email':email,'password':self.password}).status_code,200)
        self.assertEqual(self.a.get('/buildings').json()['buildings'][0]['id'],self.bid)
        self.assertEqual(self.admin.get('/admin/overview').json()['active_users'],3)

    def test_final_active_admin_and_self_protection(self):
        r=self.status('admin',False);self.assertEqual(r.status_code,409);self.assertIn('final active',r.json()['detail'])
        with self.factory() as db:
            db.get(User,self.ids['b']).role='ADMIN';db.commit()
        r=self.status('admin',False);self.assertEqual(r.status_code,409);self.assertIn('own',r.json()['detail'])
        self.assertEqual(self.admin.get('/auth/me').status_code,200)
        self.assertEqual(self.status('b',False).status_code,200)
        self.assertEqual(self.b.get('/admin/overview').status_code,401)
        self.assertEqual(self.status('admin',False).status_code,409)

    def test_last_admin_service_invariant_independent_of_self_check(self):
        from fastapi import HTTPException
        with self.factory() as db:
            with self.assertRaises(HTTPException) as failure:
                admin_service.set_user_status(db,db.get(User,self.ids['a']),self.ids['admin'],False)
            self.assertEqual(failure.exception.status_code,409)
            self.assertTrue(db.get(User,self.ids['admin']).is_active)

    def test_concurrent_admin_deactivation_cannot_remove_both(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        with self.factory() as db:
            db.get(User,self.ids['b']).role='ADMIN';db.commit()
        barrier=threading.Barrier(2)
        original=admin_service.set_user_status
        def synchronized(*args):
            barrier.wait(timeout=10)
            return original(*args)
        def deactivate(client,target):
            return client.patch(f'/admin/users/{target}/status',json={'is_active':False}).status_code
        with patch('backend.admin_service.set_user_status',side_effect=synchronized):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first=pool.submit(deactivate,self.admin,self.ids['b'])
                second=pool.submit(deactivate,self.b,self.ids['admin'])
                statuses=[first.result(),second.result()]
        self.assertEqual(sorted(statuses),[200,409])
        with self.factory() as db:
            self.assertEqual(db.scalar(select(func.count(User.id)).where(User.role=='ADMIN',User.is_active.is_(True))),1)

    def test_status_strict_payload_csrf_and_origin(self):
        url=f'/admin/users/{self.ids["a"]}/status'
        for body in [{},{'is_active':'false'},{'is_active':0},{'is_active':False,'role':'ADMIN'}]:
            self.assertEqual(self.admin.patch(url,json=body).status_code,422)
        self.assertEqual(self.admin.patch(url,json={'is_active':False},headers={'X-SmartEnergy-CSRF':''}).status_code,403)
        self.assertEqual(self.admin.patch(url,json={'is_active':False},headers={'Origin':'https://untrusted.invalid'}).status_code,403)
        self.assertTrue(self.admin.get(f'/admin/users/{self.ids["a"]}').json()['is_active'])

    def test_cross_owner_buildings_accurate_counts_ranges_and_filters(self):
        self.seed(10);other=self.create(self.b,name='Other Office',city='Filtered city',building_type='Office')
        own=self.create(self.admin,name='Admin building')
        data=self.admin.get('/admin/buildings?limit=2').json();self.assertEqual(data['total'],3);self.assertEqual(len(data['items']),2)
        self.assertEqual(data['items'][0]['measurement_count'],10)
        detail=self.admin.get(f'/admin/buildings/{self.bid}').json()
        self.assertEqual(detail['earliest_measurement_timestamp'],self.observations[0]['timestamp'].isoformat())
        self.assertEqual(detail['latest_measurement_timestamp'],self.observations[9]['timestamp'].isoformat())
        self.assertIsNone(detail['latest_prediction']);self.assertEqual(detail['owner']['id'],self.ids['a'])
        for query in ['search=Filtered%20%20city','building_type=Office',f'owner_id={self.ids["b"]}']:
            result=self.admin.get('/admin/buildings?'+query).json();self.assertEqual(result['total'],1);self.assertEqual(result['items'][0]['id'],other['id'])
        self.assertEqual(self.admin.get('/admin/buildings?offset=3').json()['items'],[])
        self.assertEqual(self.admin.get('/admin/buildings?search=%25').json()['total'],0)

    def test_real_prediction_activity_and_safe_detail(self):
        self.seed();prediction=self.predict().json()
        data=self.admin.get('/admin/predictions?limit=1').json();self.assertEqual(data['total'],1)
        row=data['items'][0];self.assertEqual(row['prediction_wh'],prediction['prediction_wh'])
        self.assertEqual(row['forecast_timestamp'],prediction['forecast_timestamp']);self.assertEqual(row['owner']['id'],self.ids['a'])
        detail=self.admin.get(f'/admin/buildings/{self.bid}').json();self.assertEqual(detail['latest_prediction'],row)
        self.assertEqual(self.admin.get('/admin/predictions?offset=1').json()['items'],[])
        for payload in [data,detail,self.admin.get('/admin/users').json()]:
            for forbidden in ['password_hash','token_hash','feature_snapshot_json','feature_hash','model_checksum','auth_sessions']:
                self.assertNotIn(forbidden,str(payload))

    def test_ordinary_owner_apis_unchanged_for_admin_and_user(self):
        self.seed(10)
        for client in [self.admin,self.b]:
            for suffix in ['', '/measurements','/predictions','/prediction-readiness','/dashboard-summary']:
                self.assertEqual(client.get(f'/buildings/{self.bid}'+suffix).status_code,404)
            self.assertEqual(client.get('/buildings').json()['buildings'],[])
        self.assertEqual(self.admin.get(f'/admin/buildings/{self.bid}').status_code,200)

    def test_bounds_missing_and_no_unsupported_mutations(self):
        for endpoint in ['users','buildings','predictions']:
            for query in ['limit=0','limit=201','offset=-1','offset=9223372036854775808']:
                self.assertEqual(self.admin.get('/admin/'+endpoint+'?'+query).status_code,422)
        for url in ['/admin/users/999999','/admin/buildings/999999']:
            self.assertEqual(self.admin.get(url).status_code,404)
        self.assertEqual(self.admin.patch('/admin/users/999999/status',json={'is_active':False}).status_code,404)
        self.assertEqual(self.admin.delete(f'/admin/users/{self.ids["a"]}').status_code,405)
        self.assertEqual(self.admin.patch(f'/admin/users/{self.ids["a"]}/role',json={'role':'ADMIN'}).status_code,404)
