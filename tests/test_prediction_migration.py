"""Phase26 upgrade/downgrade preserves legacy records without invented snapshots."""
from pathlib import Path
import os,tempfile,unittest
from unittest.mock import patch
from alembic import command
from alembic.config import Config
from sqlalchemy import text,inspect
from sqlalchemy.orm import Session
from backend.database import create_database_engine
from backend.db_models import User,Building
ROOT=Path(__file__).resolve().parents[1]

class PredictionMigrationTests(unittest.TestCase):
    def test_legacy_upgrade_downgrade_and_reupgrade(self):
        with tempfile.TemporaryDirectory() as directory:
            url='sqlite:///'+(Path(directory)/'legacy.db').as_posix()
            config=Config(str(ROOT/'alembic.ini'))
            with patch.dict(os.environ,{'DATABASE_URL':url}):
                command.upgrade(config,'0022_authentication_sessions')
                engine=create_database_engine(url)
                try:
                    with Session(engine) as db:
                        user=User(email='legacy@example.com',full_name='Migration fixture',password_hash='test-only');db.add(user);db.flush()
                        building=Building(owner_id=user.id,name='Legacy fixture');db.add(building);db.flush()
                        db.execute(text("INSERT INTO predictions (building_id, source_timestamp, prediction_wh, horizon_minutes, model_name, model_checksum, created_at) VALUES (:bid, '2016-01-18 17:00:00.000000', 10.0, 10, 'legacy-fixture', :checksum, '2026-10-23 12:00:00.000000')"),{'bid':building.id,'checksum':'0'*64});db.commit()
                    command.upgrade(config,'head')
                    with engine.connect() as db:
                        row=db.execute(text('SELECT prediction_wh, feature_hash, feature_snapshot_json FROM predictions')).one()
                        self.assertEqual(tuple(row),(10.0,None,None))
                    constraints=inspect(engine).get_unique_constraints('predictions')
                    self.assertTrue(any(c['column_names']==['building_id','source_timestamp','model_checksum','feature_hash'] for c in constraints))
                    command.downgrade(config,'0022_authentication_sessions')
                    with engine.connect() as db:self.assertEqual(db.execute(text('SELECT prediction_wh FROM predictions')).scalar_one(),10.0)
                    self.assertNotIn('feature_hash',{c['name'] for c in inspect(engine).get_columns('predictions')})
                    command.upgrade(config,'head')
                    with engine.connect() as db:self.assertEqual(db.execute(text('SELECT count(*) FROM predictions')).scalar_one(),1)
                finally:engine.dispose()
