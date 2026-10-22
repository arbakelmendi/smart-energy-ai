"""Raw ingestion, strict ownership and atomic imports in migrated disposable DBs."""
import csv, io, json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from backend.db_models import Measurement, Prediction, Building, User, RAW_MEASUREMENT_COLUMNS
from backend.measurement_service import parse_csv, MAX_BYTES
import test_buildings as fixtures
from scripts.import_uci_reference_building import import_reference, REFERENCE_NAME, REFERENCE_DESCRIPTION

FIELDS = list(RAW_MEASUREMENT_COLUMNS)
def observation(timestamp="2024-01-01T12:00:00"):
    return {"timestamp": timestamp, **dict.fromkeys(FIELDS, 1.5)}
def csv_bytes(rows=None, fields=None):
    fields = fields or ["timestamp", *FIELDS]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fields); writer.writeheader(); writer.writerows(rows if rows is not None else [observation()])
    return stream.getvalue().encode()

class MeasurementTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.BuildingTests.setUpClass.__func__)
    setUp = fixtures.BuildingTests.setUp
    tearDown = fixtures.BuildingTests.tearDown
    create = fixtures.BuildingTests.create

    def path(self):
        if not hasattr(self,'building'):
            self.building = self.create()
        return f"/buildings/{self.building['id']}/measurements"
    def upload(self, data, client=None):
        return (client or self.a).post(self.path()+'/import', files={'file':('observations.csv',data,'text/csv')})
    def total(self):return self.a.get(self.path()).json()['total']

    def test_manual_create_and_persist_exact_fields(self):
        result=self.a.post(self.path(),json=observation());self.assertEqual(result.status_code,201,result.text)
        self.assertEqual(set(result.json()),set(FIELDS)|{'timestamp','id','building_id'})
        with self.factory() as db:
            row=db.get(Measurement,result.json()['id']);self.assertEqual(row.timestamp,datetime(2024,1,1,12))
            self.assertEqual(row.Appliances,1.5)
        self.assertEqual(self.total(),1)

    def test_all_required_fields_and_no_engineered_fields(self):
        for field in ['timestamp',*FIELDS]:
            body=observation();body.pop(field)
            self.assertEqual(self.a.post(self.path(),json=body).status_code,422,field)
        for field in ['hour','lag_1','rv1','owner_id','building_id','id']:
            self.assertEqual(self.a.post(self.path(),json={**observation(),field:1}).status_code,422)
        self.assertEqual(self.total(),0)

    def test_finite_strict_numeric_values(self):
        for value in [float('nan'),float('inf'),-float('inf'),'1.2',True,None]:
            body={**observation(),'Appliances':value}
            result=self.a.post(self.path(),content=json.dumps(body),headers={'Content-Type':'application/json'})
            self.assertEqual(result.status_code,422,result.text)
        # No undocumented temperature bounds or arbitrary grid restrictions.
        self.assertEqual(self.a.post(self.path(),json={**observation('2024-01-01T12:03:17'),'T1':-90}).status_code,201)

    def test_timestamp_policy(self):
        for stamp in ['invalid','2024-01-01',123456, '2024-01-01T12:00:00Z','2024-01-01T12:00:00+01:00']:
            self.assertEqual(self.a.post(self.path(),json=observation(stamp)).status_code,422)
        self.assertEqual(self.a.post(self.path(),json=observation('2024-01-01T12:00:00.123456')).status_code,201)

    def test_duplicate_manual_timestamp_conflict(self):
        self.assertEqual(self.a.post(self.path(),json=observation()).status_code,201)
        self.assertEqual(self.a.post(self.path(),json=observation()).status_code,409);self.assertEqual(self.total(),1)

    def test_pagination_and_descending_order(self):
        self.assertEqual(self.upload(csv_bytes([observation(f'2024-01-01T12:{m:02}:00') for m in [20,0,10]])).status_code,200)
        response=self.a.get(self.path()+'?limit=1&offset=1').json()
        self.assertEqual(response['total'],3);self.assertEqual(response['limit'],1);self.assertEqual(response['offset'],1)
        self.assertEqual(response['items'][0]['timestamp'],'2024-01-01T12:10:00')
        self.assertEqual(response['first_timestamp'],'2024-01-01T12:00:00');self.assertEqual(response['last_timestamp'],'2024-01-01T12:20:00')
        self.assertEqual(self.a.get(self.path()+'?offset=100').json()['items'],[])
        for query in ['limit=0','limit=501','offset=-1','offset=9223372036854775808']:
            self.assertEqual(self.a.get(self.path()+'?'+query).status_code,422)

    def test_empty_history_factual_metadata(self):
        self.assertEqual(self.a.get(self.path()).json(),{'items':[],'total':0,'limit':100,'offset':0,'first_timestamp':None,'last_timestamp':None})

    def test_anonymous_and_other_owner_all_routes(self):
        row=self.a.post(self.path(),json=observation()).json()
        with TestClient(fixtures.app,base_url='http://localhost',headers={'X-SmartEnergy-CSRF':'1'}) as anonymous:
            for client,status in [(anonymous,401),(self.b,404),(self.admin,404)]:
                self.assertEqual(client.get(self.path()).status_code,status)
                self.assertEqual(client.post(self.path(),json=observation()).status_code,status)
                self.assertEqual(self.upload(csv_bytes(),client).status_code,status)
                self.assertEqual(client.delete(self.path()+f"/{row['id']}").status_code,status)
        self.assertEqual(self.total(),1)

    def test_admin_own_history(self):
        own=self.create(self.admin)
        path=f"/buildings/{own['id']}/measurements"
        self.assertEqual(self.admin.post(path,json=observation()).status_code,201)
        self.assertEqual(self.admin.get(path).json()['total'],1)
        self.assertEqual(self.a.get(path).status_code,404)

    def test_delete_and_building_mismatch(self):
        row=self.a.post(self.path(),json=observation()).json()
        other=self.create();otherpath=f"/buildings/{other['id']}/measurements/{row['id']}"
        self.assertEqual(self.a.delete(otherpath).status_code,404)
        response=self.a.delete(self.path()+f"/{row['id']}");self.assertEqual(response.status_code,204);self.assertEqual(response.content,b'')
        self.assertEqual(self.total(),0)

    def test_csrf_and_no_store(self):
        for endpoint in [self.path(),self.path()+'/import']:
            self.assertEqual(self.a.post(endpoint,headers={'X-SmartEnergy-CSRF':''},json=observation()).status_code,403)
        self.assertEqual(self.a.delete(self.path()+'/1',headers={'X-SmartEnergy-CSRF':''}).status_code,403)
        self.assertEqual(self.a.get(self.path()).headers['cache-control'],'no-store')

    def test_csv_date_alias_and_ignored_random_columns(self):
        row=observation();row['date']=row.pop('timestamp');row.update(rv1='ignored',rv2='ignored')
        response=self.upload(csv_bytes([row],['date',*FIELDS,'rv1','rv2']))
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['rows_imported'],1);self.assertEqual(response.json()['ignored_columns'],['rv1','rv2'])
        self.assertNotIn('rv1',self.a.get(self.path()).json()['items'][0])

    def test_csv_invalid_headers(self):
        cases=[b'',b'timestamp,Appliances\n2024-01-01T12:00:00,1\n',
               csv_bytes([{**observation(),'hour':1}],['timestamp',*FIELDS,'hour']),
               csv_bytes([{**observation(),'date':'2024-01-01T12:00:00'}],['timestamp','date',*FIELDS]),b'timestamp,timestamp\n1,1\n']
        for data in cases:self.assertEqual(self.upload(data).status_code,422)
        self.assertEqual(self.total(),0)

    def test_csv_malformed_rows_and_atomicity(self):
        for field,value in [('T1','bad'),('Appliances','NaN'),('T2','inf'),('timestamp','not-a-date'),('timestamp','2024-01-01T12:10:00Z')]:
            rows=[observation(),{**observation('2024-01-01T12:10:00'),field:value}]
            result=self.upload(csv_bytes(rows));self.assertEqual(result.status_code,422,result.text)
            self.assertEqual(result.json()['detail'][0]['row'],3);self.assertEqual(self.total(),0)
        for data in [csv_bytes()+b'extra,bad,row\n',b'\xff',csv_bytes([]),b'"unclosed']:
            self.assertEqual(self.upload(data).status_code,422)
            self.assertEqual(self.total(),0)

    def test_csv_duplicates_in_file_and_database(self):
        self.assertEqual(self.upload(csv_bytes([observation(),observation()])).status_code,422);self.assertEqual(self.total(),0)
        self.a.post(self.path(),json=observation())
        result=self.upload(csv_bytes([observation('2024-01-01T12:10:00'),observation()]))
        self.assertEqual(result.status_code,409);self.assertEqual(self.total(),1)

    def test_batch_import_no_ml_or_predictions(self):
        from datetime import timedelta
        rows=[observation((datetime(2024,1,1)+timedelta(minutes=i*10)).isoformat()) for i in range(1201)]
        with patch('backend.services.inference.load_final_model',side_effect=AssertionError('No ML during ingestion')):
            response=self.upload(csv_bytes(rows))
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['rows_imported'],1201)
        with self.factory() as db:self.assertEqual(db.scalar(select(func.count(Prediction.id))),0)
        self.assertEqual(self.total(),1201)

    def test_size_and_row_limits(self):
        self.assertEqual(self.upload(b'x'*(MAX_BYTES+1)).status_code,413)
        with patch('backend.measurement_service.MAX_ROWS',1):
            self.assertEqual(self.upload(csv_bytes([observation(),observation('2024-01-01T12:10:00')])).status_code,422)
        self.assertEqual(self.total(),0)

    def test_reference_import_and_repeat_collision_policies(self):
        source=Path(self.directory.name)/'reference.csv';source.write_bytes(csv_bytes())
        with self.factory() as db:
            email=db.get(User,self.ids['admin']).email
            result=import_reference(db,email,source);self.assertEqual(result['rows_imported'],1)
            building=db.get(Building,result['building_id']);self.assertEqual(building.name,REFERENCE_NAME);self.assertIsNone(building.city)
            self.assertEqual(building.owner_id,self.ids['admin']);self.assertEqual(building.description,REFERENCE_DESCRIPTION)
            with self.assertRaises(ValueError):import_reference(db,email,source)
            with self.assertRaises(ValueError):import_reference(db,db.get(User,self.ids['a']).email,source)
        self.assertEqual(self.admin.get('/buildings').json()['buildings'][0]['id'],result['building_id'])
        self.assertEqual(self.a.get(f"/buildings/{result['building_id']}/measurements").status_code,404)

    def test_reference_invalid_source_creates_nothing(self):
        source=Path(self.directory.name)/'reference.csv';source.write_bytes(b'bad')
        with self.factory() as db:
            email=db.get(User,self.ids['admin']).email
            from fastapi import HTTPException
            with self.assertRaises(HTTPException):import_reference(db,email,source)
            self.assertEqual(db.scalar(select(func.count(Building.id))),0)
            db.add(Building(owner_id=self.ids['admin'],name=REFERENCE_NAME,description='Unrelated'));db.commit()
            with self.assertRaises(ValueError):import_reference(db,email,source)

    def test_late_batch_database_failure_rolls_back_earlier_batches(self):
        from datetime import timedelta
        from fastapi import HTTPException
        from sqlalchemy.exc import IntegrityError
        from backend.measurement_service import persist_rows
        rows=[{**dict.fromkeys(FIELDS,1.0),"timestamp":datetime(2024,1,1)+timedelta(minutes=i)} for i in range(501)]
        self.path()
        with self.factory() as db:
            original=db.execute; writes=0
            def fail_second(statement,*args,**kwargs):
                nonlocal writes
                if getattr(statement,'is_insert',False):
                    writes+=1
                    if writes==2:raise IntegrityError('test-only injected constraint failure',{},None)
                return original(statement,*args,**kwargs)
            with patch.object(db,'execute',side_effect=fail_second):
                with self.assertRaises(HTTPException) as error:persist_rows(db,self.building['id'],rows)
                self.assertEqual(error.exception.status_code,409)
            self.assertEqual(db.scalar(select(func.count(Measurement.id))),0)
