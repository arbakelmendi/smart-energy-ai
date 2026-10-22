"""Owner-isolated building CRUD with real session dependencies and temporary DB."""
from datetime import datetime
import os
from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func,select
from sqlalchemy.orm import sessionmaker

from backend.auth import hash_password
from backend.database import create_database_engine,get_db
from backend.db_models import Building,Measurement,Prediction,RAW_MEASUREMENT_COLUMNS,User
from backend.main import app

ROOT=Path(__file__).resolve().parents[1]


class BuildingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password=secrets.token_urlsafe(24)
        cls.encoded=hash_password(cls.password)

    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.url='sqlite:///'+(Path(self.directory.name)/'buildings.db').as_posix()
        self.env=patch.dict(os.environ,{'DATABASE_URL':self.url,'SMARTENERGY_COOKIE_SECURE':'false'})
        self.env.start();command.upgrade(Config(str(ROOT/'alembic.ini')),'head')
        self.engine=create_database_engine(self.url);self.factory=sessionmaker(self.engine,expire_on_commit=False)
        self.previous=app.dependency_overrides.copy()
        def isolated():
            with self.factory() as db:yield db
        app.dependency_overrides[get_db]=isolated
        self.clients=[];self.ids={}
        with self.factory() as db:
            for name,role in [('a','USER'),('b','USER'),('admin','ADMIN')]:
                user=User(email=name+'-'+secrets.token_hex(6)+'@example.com',full_name='Isolated '+name,password_hash=self.encoded,role=role)
                db.add(user);db.flush();self.ids[name]=user.id
                client=TestClient(app,base_url='http://localhost',headers={'X-SmartEnergy-CSRF':'1'})
                self.clients.append(client)
                setattr(self,name,client)
                # Login after committing account; get_current_user remains real.
                db.commit()
                response=client.post('/auth/login',json={'email':user.email,'password':self.password})
                self.assertEqual(response.status_code,200)

    def tearDown(self):
        for client in self.clients:client.close()
        app.dependency_overrides.clear();app.dependency_overrides.update(self.previous)
        self.engine.dispose();self.env.stop();self.directory.cleanup()

    def create(self,client=None,**body):
        response=(client or self.a).post('/buildings',json={'name':'Building fixture',**body})
        self.assertEqual(response.status_code,201,response.text)
        return response.json()

    def test_create_owner_trimmed_and_safe_response(self):
        building=self.create(name='  First building  ',city='  City  ',building_type='Office',floor_area_m2=123.5,description='Description')
        self.assertEqual(building['name'],'First building');self.assertEqual(building['city'],'City')
        self.assertEqual(set(building),{'id','name','building_type','floor_area_m2','city','description','created_at','updated_at'})
        with self.factory() as db:self.assertEqual(db.get(Building,building['id']).owner_id,self.ids['a'])

    def test_empty_list_no_seeded_building(self):
        self.assertEqual(self.a.get('/buildings').json(),{'buildings':[]})

    def test_authentication_required_all_operations(self):
        building=self.create()
        with TestClient(app,base_url='http://localhost',headers={'X-SmartEnergy-CSRF':'1'}) as anonymous:
            for method,path,body in [('GET','/buildings',None),('GET',f"/buildings/{building['id']}",None),('POST','/buildings',{'name':'No'}),('PATCH',f"/buildings/{building['id']}",{'name':'No'}),('DELETE',f"/buildings/{building['id']}",None)]:
                self.assertEqual(anonymous.request(method,path,**({'json':body} if body is not None else {})).status_code,401)

    def test_list_only_owner_and_id_order(self):
        first=self.create(name='Z');self.create(self.b,name='Other');last=self.create(name='A')
        self.assertEqual([x['id'] for x in self.a.get('/buildings').json()['buildings']],[first['id'],last['id']])
        self.assertEqual([x['name'] for x in self.b.get('/buildings').json()['buildings']],['Other'])

    def test_get_own_and_uniform_404(self):
        building=self.create();path=f"/buildings/{building['id']}"
        self.assertEqual(self.a.get(path).json(),building)
        hidden=self.b.get(path);missing=self.b.get('/buildings/99999')
        self.assertEqual(hidden.status_code,404);self.assertEqual(hidden.json(),missing.json())

    def test_update_own_partial_and_timestamps(self):
        building=self.create(city='Old',description='Keep')
        response=self.a.patch(f"/buildings/{building['id']}",json={'name':'  Renamed  ','floor_area_m2':42})
        self.assertEqual(response.status_code,200);saved=response.json()
        self.assertEqual(saved['name'],'Renamed');self.assertEqual(saved['description'],'Keep')
        self.assertEqual(saved['city'],'Old');self.assertEqual(saved['floor_area_m2'],42)
        self.assertEqual(saved['created_at'],building['created_at']);self.assertGreaterEqual(saved['updated_at'],building['updated_at'])

    def test_other_user_cannot_update_or_delete(self):
        building=self.create();path=f"/buildings/{building['id']}"
        self.assertEqual(self.b.patch(path,json={'name':'Intrusion'}).status_code,404)
        self.assertEqual(self.b.delete(path).status_code,404)
        self.assertEqual(self.a.get(path).json()['name'],building['name'])

    def test_owner_and_immutable_fields_injection_rejected(self):
        building=self.create();path=f"/buildings/{building['id']}"
        for field,value in [('owner_id',self.ids['b']),('id',99),('created_at','2020-01-01T00:00:00'),('updated_at','2020-01-01T00:00:00')]:
            with self.subTest(field=field):
                self.assertEqual(self.a.post('/buildings',json={'name':'Bad',field:value}).status_code,422)
                self.assertEqual(self.a.patch(path,json={field:value}).status_code,422)

    def test_delete_own_204_then_missing(self):
        building=self.create();path=f"/buildings/{building['id']}"
        response=self.a.delete(path);self.assertEqual(response.status_code,204);self.assertEqual(response.content,b'')
        self.assertEqual(self.a.get(path).status_code,404);self.assertEqual(self.a.get('/buildings').json(),{'buildings':[]})

    def test_cascade_to_real_test_only_child_rows(self):
        building=self.create();origin=datetime(2016,1,18,17)
        with self.factory() as db:
            db.add(Measurement(building_id=building['id'],timestamp=origin,**{n:1.0 for n in RAW_MEASUREMENT_COLUMNS}))
            db.add(Prediction(building_id=building['id'],source_timestamp=origin,prediction_wh=1,model_name='test-only',model_checksum='0'*64))
            db.commit()
        self.assertEqual(self.a.delete(f"/buildings/{building['id']}").status_code,204)
        with self.factory() as db:
            for model in (Building,Measurement,Prediction):self.assertEqual(db.scalar(select(func.count()).select_from(model)),0)

    def test_optional_fields_and_null_clear(self):
        building=self.create();self.assertIsNone(building['building_type']);self.assertIsNone(building['floor_area_m2'])
        path=f"/buildings/{building['id']}"
        self.assertEqual(self.a.patch(path,json={'city':'City','description':'Text','floor_area_m2':4,'building_type':'Other'}).status_code,200)
        result=self.a.patch(path,json={'city':None,'description':None,'floor_area_m2':None,'building_type':None}).json()
        self.assertTrue(all(result[n] is None for n in ('city','description','floor_area_m2','building_type')))

    def test_invalid_names_and_empty_patch(self):
        for value in ('','   ','x'*201,None):
            self.assertEqual(self.a.post('/buildings',json={'name':value}).status_code,422)
        building=self.create();path=f"/buildings/{building['id']}"
        for body in ({},{'name':None},{'name':'  '}):self.assertEqual(self.a.patch(path,json=body).status_code,422)

    def test_area_validation_create_and_patch(self):
        building=self.create();path=f"/buildings/{building['id']}"
        for value in (0,-1,'2',True):
            self.assertEqual(self.a.post('/buildings',json={'name':'Bad','floor_area_m2':value}).status_code,422)
            self.assertEqual(self.a.patch(path,json={'floor_area_m2':value}).status_code,422)
        for literal in ('NaN','Infinity','-Infinity'):
            for method,target,body in [('POST','/buildings','{"name":"Bad","floor_area_m2":'+literal+'}'),('PATCH',path,'{"floor_area_m2":'+literal+'}')]:
                self.assertEqual(self.a.request(method,target,content=body,headers={'Content-Type':'application/json'}).status_code,422)

    def test_controlled_type_and_text_lengths(self):
        for body in ({'building_type':'Castle'},{'city':'x'*201},{'description':'x'*4001}):
            self.assertEqual(self.a.post('/buildings',json={'name':'Bad',**body}).status_code,422)
        for value in ('Residential','Office','Educational','Healthcare','Retail','Industrial','Other'):
            self.create(building_type=value)
        self.assertIsNone(self.create(city='  ')['city'])

    def test_admin_same_owner_only_policy(self):
        other=self.create();own=self.create(self.admin,name='Admin owned')
        self.assertEqual([b['id'] for b in self.admin.get('/buildings').json()['buildings']],[own['id']])
        path=f"/buildings/{other['id']}"
        self.assertEqual(self.admin.get(path).status_code,404)
        self.assertEqual(self.admin.patch(path,json={'name':'Cross owner'}).status_code,404)
        self.assertEqual(self.admin.delete(path).status_code,404)
        self.assertEqual(self.admin.patch(f"/buildings/{own['id']}",json={'name':'Updated admin owned'}).status_code,200)
        self.assertEqual(self.admin.delete(f"/buildings/{own['id']}").status_code,204)

    def test_csrf_required_on_every_mutation(self):
        building=self.create();path=f"/buildings/{building['id']}"
        with TestClient(app,base_url='http://localhost',cookies=self.a.cookies) as missing_header:
            for method,target,body in [('POST','/buildings',{'name':'No'}),('PATCH',path,{'name':'No'}),('DELETE',path,None)]:
                self.assertEqual(missing_header.request(method,target,**({'json':body} if body else {})).status_code,403)
        self.assertEqual(self.a.patch(path,json={'name':'No'},headers={'Origin':'https://untrusted.example'}).status_code,403)

    def test_credentialed_cors_patch_delete(self):
        for method in ('PATCH','DELETE'):
            result=self.a.options('/buildings/1',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':method,'Access-Control-Request-Headers':'Content-Type,X-SmartEnergy-CSRF'})
            self.assertEqual(result.status_code,200);self.assertEqual(result.headers['access-control-allow-credentials'],'true')

    def test_private_reads_and_writes_no_store(self):
        building=self.create()
        for response in (self.a.get('/buildings'),self.a.get(f"/buildings/{building['id']}"),self.b.get(f"/buildings/{building['id']}")):
            self.assertEqual(response.headers['cache-control'],'no-store')

    def test_invalid_path_ids_rejected_without_sql_overflow(self):
        for value in ('0','-1','abc','9223372036854775808'):
            self.assertEqual(self.a.get('/buildings/'+value).status_code,422)

    def test_inactive_session_blocked_and_no_model_execution(self):
        with patch('ml.src.model_inference.load_final_model',side_effect=AssertionError('CRUD must not load model')), patch('ml.src.model_inference.predict_next_appliances',side_effect=AssertionError('CRUD must not predict')):
            self.create();self.assertEqual(self.a.get('/buildings').status_code,200)
        with self.factory() as db:
            user=db.get(User,self.ids['a']);user.is_active=False;db.commit()
        self.assertEqual(self.a.get('/buildings').status_code,401)


if __name__=='__main__':unittest.main()
