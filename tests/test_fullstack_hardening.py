"""New adversarial cases for existing completed application behavior; temporary DB only."""
import io,json,secrets,threading,unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import delete,func,insert,select
from sqlalchemy.exc import OperationalError
import test_building_predictions as fixtures
from backend import auth,admin_service,services
from backend.db_models import User,AuthSession,Building,Measurement,Prediction
from backend.main import app

class FullstackHardeningTests(unittest.TestCase):
    setUpClass=classmethod(fixtures.BuildingPredictionTests.setUpClass.__func__)
    setUp=fixtures.BuildingPredictionTests.setUp
    tearDown=fixtures.BuildingPredictionTests.tearDown
    create=fixtures.BuildingPredictionTests.create
    path=fixtures.BuildingPredictionTests.path
    seed=fixtures.BuildingPredictionTests.seed
    predict=fixtures.BuildingPredictionTests.predict

    def test_login_racing_deactivation_cannot_issue_a_revivable_session(self):
        entered=threading.Event();resume=threading.Event();original=auth.establish_session
        with self.factory() as db:email=db.get(User,self.ids['a']).email
        def paused(*args):
            entered.set();self.assertTrue(resume.wait(10));return original(*args)
        client=TestClient(app,base_url='http://localhost',headers={'X-SmartEnergy-CSRF':'1'});self.clients.append(client)
        with patch('backend.auth.establish_session',side_effect=paused):
            with ThreadPoolExecutor(max_workers=1) as pool:
                pending=pool.submit(client.post,'/auth/login',json={'email':email,'password':self.password})
                try:
                    self.assertTrue(entered.wait(10))
                    self.assertEqual(self.admin.patch(f'/admin/users/{self.ids["a"]}/status',json={'is_active':False}).status_code,200)
                finally:resume.set()
                response=pending.result()
        self.assertEqual(response.status_code,401,response.text)
        with self.factory() as db:self.assertEqual(db.scalar(select(func.count(AuthSession.id)).where(AuthSession.user_id==self.ids['a'])),0)
        self.admin.patch(f'/admin/users/{self.ids["a"]}/status',json={'is_active':True})
        self.assertEqual(client.get('/auth/me').status_code,401)

    def test_authorization_idor_matrix_including_second_admin(self):
        self.seed(2)
        with self.factory() as db:
            b=db.get(User,self.ids['b']);b.role='ADMIN';db.commit()
            mid=db.scalar(select(Measurement.id).where(Measurement.building_id==self.bid))
        own_b=self.create(self.b)['id']
        with TestClient(app,base_url='http://localhost',headers={'X-SmartEnergy-CSRF':'1'}) as anon:
            for actor,expected in [(anon,401),(self.a,200),(self.b,404),(self.admin,404)]:
                for suffix in ['', '/measurements','/prediction-readiness','/predictions','/dashboard-summary']:
                    with self.subTest(actor=expected,endpoint=suffix):self.assertEqual(actor.get(f'/buildings/{self.bid}'+suffix).status_code,expected)
            for actor in [self.b,self.admin]:
                for method,suffix,body in [('PATCH','',{'name':'IDOR'}),('DELETE','',None),('POST','/measurements',self.observations[2]|{'timestamp':self.observations[2]['timestamp'].isoformat()}),('DELETE',f'/measurements/{mid}',None),('POST','/predictions',None)]:
                    self.assertEqual(actor.request(method,f'/buildings/{self.bid}'+suffix,**({'json':body} if body else {})).status_code,404)
                self.assertEqual(actor.post(f'/buildings/{self.bid}/measurements/import',files={'file':('bad.csv',b'bad')}).status_code,404)
            self.assertEqual(self.b.delete(f'/buildings/{own_b}/measurements/{mid}').status_code,404)
            for actor,expected in [(anon,401),(self.a,403),(self.b,200),(self.admin,200)]:
                for path in ['/admin/overview','/admin/users',f'/admin/users/{self.ids["a"]}','/admin/buildings',f'/admin/buildings/{self.bid}','/admin/predictions']:
                    self.assertEqual(actor.get(path).status_code,expected)
        self.assertEqual(self.a.get(f'/buildings/{self.bid}/measurements').json()['total'],2)

    def test_csrf_inventory_all_current_mutations_and_untrusted_origin(self):
        self.seed(1)
        with self.factory() as db:mid=db.scalar(select(Measurement.id))
        specs=[(self.a,'POST','/auth/logout',None),(self.a,'POST','/buildings',{'name':'Denied'}),
            (self.a,'PATCH',f'/buildings/{self.bid}',{'name':'Denied'}),(self.a,'DELETE',f'/buildings/{self.bid}',None),
            (self.a,'POST',f'/buildings/{self.bid}/measurements',{}),(self.a,'DELETE',f'/buildings/{self.bid}/measurements/{mid}',None),
            (self.a,'POST',f'/buildings/{self.bid}/predictions',None),
            (self.admin,'PATCH',f'/admin/users/{self.ids["a"]}/status',{'is_active':False})]
        for client,method,path,body in specs:
            for headers in [{'X-SmartEnergy-CSRF':''},{'X-SmartEnergy-CSRF':'wrong'},{'Origin':'https://attacker.invalid'}]:
                with self.subTest(path=path,headers=headers):
                    self.assertEqual(client.request(method,path,headers=headers,**({'json':body} if body is not None else {})).status_code,403)
        self.assertEqual(self.a.post(f'/buildings/{self.bid}/measurements/import',files={'file':('x.csv',b'bad')},headers={'X-SmartEnergy-CSRF':''}).status_code,403)
        self.assertEqual(self.a.get('/auth/me').status_code,200)
        self.assertEqual(self.a.get(f'/buildings/{self.bid}/measurements').json()['total'],1)

    def test_untrusted_preflight_and_actual_mutation_does_not_change_state(self):
        for origin,expected in [('http://localhost:5173',200),('https://attacker.invalid',400),('null',400)]:
            r=self.a.options('/buildings',headers={'Origin':origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Content-Type,X-SmartEnergy-CSRF'})
            self.assertEqual(r.status_code,expected)
            self.assertEqual(r.headers.get('access-control-allow-origin'),origin if expected==200 else None)
        self.assertEqual(self.a.post('/buildings',json={'name':'Denied'},headers={'Origin':'https://attacker.invalid'}).status_code,403)
        self.assertEqual(self.a.get('/buildings').json()['buildings'],[])

    def test_failed_signup_and_admin_transaction_roll_back_and_do_not_leak(self):
        failure=OperationalError('private SQL and filesystem',{'password':'private-value'},Exception('private diagnostic'))
        with self.factory() as db:
            total=db.scalar(select(func.count(User.id)));sessions=db.scalar(select(func.count(AuthSession.id)))
        with patch('sqlalchemy.orm.Session.commit',side_effect=failure):
            signup=self.a.post('/auth/signup',json={'email':'rollback-'+secrets.token_hex(4)+'@example.com','full_name':'Rollback fixture','password':self.password})
            status=self.admin.patch(f'/admin/users/{self.ids["a"]}/status',json={'is_active':False})
        for response in [signup,status]:
            self.assertEqual(response.status_code,503);self.assertNotIn('private',response.text);self.assertNotIn('Traceback',response.text)
        with self.factory() as db:
            self.assertEqual(db.scalar(select(func.count(User.id))),total)
            self.assertEqual(db.scalar(select(func.count(AuthSession.id))),sessions)
            self.assertTrue(db.get(User,self.ids['a']).is_active)
        self.assertEqual(self.a.get('/auth/me').status_code,200)

    def test_duplicate_normalized_signup_race_one_account(self):
        email='race-'+secrets.token_hex(6)+'@example.com'
        clients=[TestClient(app,base_url='http://localhost',headers={'X-SmartEnergy-CSRF':'1'}) for _ in range(2)];self.clients.extend(clients)
        barrier=threading.Barrier(2);original=auth.hash_password
        def paused(value):barrier.wait(timeout=10);return original(value)
        with patch('backend.auth.hash_password',side_effect=paused):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(lambda pair:pair[0].post('/auth/signup',json={'email':pair[1],'password':self.password,'full_name':'Concurrent fixture'}).status_code,zip(clients,[email,email.upper()])))
        self.assertEqual(sorted(results),[201,409])
        with self.factory() as db:self.assertEqual(db.scalar(select(func.count(User.id)).where(User.email==email)),1)

    def test_duplicate_measurement_insert_race_and_deleted_parent_safety(self):
        self.path()
        body=self.observations[0]|{'timestamp':self.observations[0]['timestamp'].isoformat()}
        token=self.a.cookies.get(auth.COOKIE_NAME)
        other=TestClient(app,base_url='http://localhost',headers={'X-SmartEnergy-CSRF':'1','Cookie':auth.COOKIE_NAME+'='+token});self.clients.append(other)
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses=list(pool.map(lambda client:client.post(f'/buildings/{self.bid}/measurements',json=body).status_code,[self.a,other]))
        self.assertEqual(sorted(statuses),[201,409])
        from backend import measurement_service
        original=measurement_service.persist_rows
        def deleted(db,bid,rows,ignored_columns=()):
            with self.factory() as concurrent:concurrent.execute(delete(Building).where(Building.id==bid));concurrent.commit()
            return original(db,bid,rows,ignored_columns)
        with patch('backend.measurement_service.persist_rows',side_effect=deleted):
            result=self.a.post(f'/buildings/{self.bid}/measurements',json=self.observations[1]|{'timestamp':self.observations[1]['timestamp'].isoformat()})
        self.assertEqual(result.status_code,409)
        with self.factory() as db:self.assertEqual(db.scalar(select(func.count(Measurement.id))),0)

    def test_parent_deleted_during_forecasting_has_no_orphan(self):
        self.seed();original=services.recommendations.predict_and_recommend
        def deleted(*args,**kwargs):
            result=original(*args,**kwargs)
            with self.factory() as db:db.execute(delete(Building).where(Building.id==self.bid));db.commit()
            return result
        with patch('backend.services.recommendations.predict_and_recommend',side_effect=deleted):response=self.predict()
        self.assertEqual(response.status_code,409)
        with self.factory() as db:self.assertEqual(db.scalar(select(func.count(Prediction.id))),0)

    def test_sql_search_injection_is_literal_and_safe(self):
        name="' OR 1=1 -- % _"
        self.create(name=name)
        for query in ["' OR 1=1 --",'%','_']:
            r=self.admin.get('/admin/buildings',params={'search':query});self.assertEqual(r.status_code,200);self.assertEqual(r.json()['total'],1)
            self.assertEqual(self.admin.get('/admin/users',params={'search':query}).json()['total'],0)
        self.assertEqual(self.admin.get('/admin/users').json()['total'],3)

    def test_model_corruption_is_safe_without_altering_actual_artifact(self):
        self.seed()
        with patch('backend.services.inference.load_final_model',side_effect=ValueError('private corrupt artifact path')):
            r=self.predict();self.assertEqual(r.status_code,503);self.assertNotIn('private',r.text)
        self.assertEqual(self.a.get(f'/buildings/{self.bid}/measurements').status_code,200)
        self.assertEqual(self.a.get(f'/buildings/{self.bid}/predictions').status_code,200)
        self.assertEqual(self.admin.get('/admin/overview').json()['total_predictions'],0)

    def test_csv_adversarial_inputs_atomic_and_full_uci_size_supported(self):
        import csv
        self.path()
        source=(fixtures.fixtures.ROOT/'data/raw/energydata_complete.csv').read_bytes()
        reader=csv.reader(io.StringIO(source.decode('utf-8')));header=next(reader);first=next(reader)
        def encoded(headers,rows):
            out=io.StringIO();writer=csv.writer(out);writer.writerow(headers);writer.writerows(rows);return out.getvalue().encode()
        nan=list(first);nan[header.index('Appliances')]='NaN'
        inf=list(first);inf[header.index('Appliances')]='inf'
        wrong=list(first);wrong[0]='2016-01-01T00:00:00+01:00'
        malformed=list(first);malformed[header.index('Appliances')]='oops'
        cases=[b'',encoded(header,[]),b'\xff\xfe',encoded(header+[header[1]],[first+[first[1]]]),
            encoded(header[1:],[first[1:]]),encoded(header+['occupancy'],[first+['1']]),
            encoded(header,[first,first]),encoded(header,[first,nan]),encoded(header,[first,inf]),
            encoded(header,[first,wrong]),encoded(header,[first,malformed]),b'x'*(16*1024*1024+1)]
        for content in cases:
            with self.subTest(bytes=len(content)):
                r=self.a.post(f'/buildings/{self.bid}/measurements/import',files={'file':('fixture.csv',content,'text/csv')})
                self.assertIn(r.status_code,[413,422]);self.assertEqual(self.a.get(f'/buildings/{self.bid}/measurements').json()['total'],0)
        result=self.a.post(f'/buildings/{self.bid}/measurements/import',files={'file':('uci.csv',source,'text/csv')})
        self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.json()['rows_imported'],19735)
        self.assertEqual(result.json()['ignored_columns'],['rv1','rv2'])
        duplicate=self.a.post(f'/buildings/{self.bid}/measurements/import',files={'file':('again.csv',encoded(header,[first]))})
        self.assertEqual(duplicate.status_code,409);self.assertEqual(self.a.get(f'/buildings/{self.bid}/measurements').json()['total'],19735)

    def test_two_sessions_logout_only_current_and_deactivation_revokes_rest(self):
        with self.factory() as db:email=db.get(User,self.ids['a']).email
        other=TestClient(app,base_url='http://localhost',headers={'X-SmartEnergy-CSRF':'1'});self.clients.append(other)
        self.assertEqual(other.post('/auth/login',json={'email':email,'password':self.password}).status_code,200)
        token=other.cookies.get(auth.COOKIE_NAME)
        self.assertEqual(self.a.post('/auth/logout').status_code,200)
        self.assertEqual(other.get('/auth/me').status_code,200)
        self.admin.patch(f'/admin/users/{self.ids["a"]}/status',json={'is_active':False})
        self.admin.patch(f'/admin/users/{self.ids["a"]}/status',json={'is_active':True})
        self.assertEqual(other.get('/auth/me',headers={'Cookie':auth.COOKIE_NAME+'='+token}).status_code,401)
