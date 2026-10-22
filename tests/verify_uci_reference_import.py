"""Full local CSV import verification in a temporary DB; never developer data."""
from pathlib import Path
import csv, hashlib, json, os, secrets, subprocess, sys, tempfile, time
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
    source=ROOT/'data/raw/energydata_complete.csv'
    checksum=hashlib.sha256(source.read_bytes()).hexdigest()
    with source.open(newline='',encoding='utf-8') as stream:rows=list(csv.DictReader(stream))
    from datetime import datetime
    timestamps=[datetime.fromisoformat(row['date']) for row in rows]
    assert all((b-a).total_seconds()==600 for a,b in zip(timestamps,timestamps[1:]))
    with tempfile.TemporaryDirectory(prefix='phase24-uci-') as directory:
        url='sqlite:///'+(Path(directory)/'reference.db').as_posix()
        with patch.dict(os.environ,{'DATABASE_URL':url}):
            from alembic import command
            from alembic.config import Config
            from sqlalchemy import select,func
            from sqlalchemy.orm import Session
            from backend.database import create_database_engine
            from backend.db_models import Measurement,Prediction,Building,User,RAW_MEASUREMENT_COLUMNS
            from backend.auth import hash_password
            from datetime import datetime
            command.upgrade(Config(str(ROOT/'alembic.ini')),'head')
            engine=create_database_engine(url)
            email='verification-'+secrets.token_hex(8)+'@example.com'
            with Session(engine) as db:
                db.add(User(email=email,full_name='Temporary reference admin',password_hash=hash_password(secrets.token_urlsafe(24)),role='ADMIN'));db.commit()
            started=time.perf_counter()
            result=subprocess.run([sys.executable,str(ROOT/'scripts/import_uci_reference_building.py'),'--admin-email',email],capture_output=True,text=True,cwd=ROOT)
            elapsed=time.perf_counter()-started
            assert result.returncode==0,result.stderr
            response=json.loads(result.stdout)
            with Session(engine) as db:
                stored=db.scalars(select(Measurement).order_by(Measurement.timestamp)).all()
                assert len(stored)==len(rows)==response['rows_imported']
                for actual,expected in zip(stored,rows):
                    assert actual.timestamp==datetime.fromisoformat(expected['date'])
                    assert all(getattr(actual,f)==float(expected[f]) for f in RAW_MEASUREMENT_COLUMNS)
                assert not {'rv1','rv2'} & set(Measurement.__table__.columns.keys())
                assert db.scalar(select(func.count(Prediction.id)))==0
                assert db.scalar(select(func.count(Building.id)))==1
                duplicate=db.execute(select(Measurement.timestamp).group_by(Measurement.building_id,Measurement.timestamp).having(func.count()>1)).first()
                assert duplicate is None
            repeat=subprocess.run([sys.executable,str(ROOT/'scripts/import_uci_reference_building.py'),'--admin-email',email],capture_output=True,text=True,cwd=ROOT)
            assert repeat.returncode==1
            with Session(engine) as db:
                assert db.scalar(select(func.count(Measurement.id)))==len(rows)
                assert db.scalar(select(func.count(Building.id)))==1
            engine.dispose()
    assert hashlib.sha256(source.read_bytes()).hexdigest()==checksum
    evidence={'passed':True,'source_rows':len(rows),'imported_rows':response['rows_imported'],'all_26_values_and_timestamps_match_source':True,'first_timestamp':response['first_timestamp'],'last_timestamp':response['last_timestamp'],'ignored_columns':response['ignored_columns'],'no_random_columns_stored':True,'no_duplicates':True,'source_exact_10_minute_continuity_verified':True,'no_predictions_created':True,'repeat_import_safely_rejected':True,'import_seconds':round(elapsed,3),'source_sha256_unchanged':checksum,'temporary_db_removed':True}
    (ROOT/'ml/results/generated/phase24_uci_verification.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence,indent=2))

if __name__=='__main__':main()
