"""Fresh and incremental actual Alembic lineage; no developer database access."""
import io,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect,text
from sqlalchemy.orm import Session
from backend.database import Base,create_database_engine
from backend.db_models import User,Building
ROOT=Path(__file__).resolve().parents[1]

class MigrationHardeningTests(unittest.TestCase):
    def test_empty_phase21_phase22_upgrade_paths_and_legacy_preservation(self):
        for origin in [None,'0021_database_foundation','0022_authentication_sessions']:
            with self.subTest(origin=origin),tempfile.TemporaryDirectory() as directory:
                url='sqlite:///'+(Path(directory)/'migration.db').as_posix();stdout=io.StringIO();config=Config(str(ROOT/'alembic.ini'),stdout=stdout)
                scripts=ScriptDirectory.from_config(config)
                self.assertEqual(scripts.get_heads(),['0026_prediction_feature_snapshots'])
                self.assertEqual([r.revision for r in scripts.walk_revisions()],['0026_prediction_feature_snapshots','0022_authentication_sessions','0021_database_foundation'])
                with patch.dict(os.environ,{'DATABASE_URL':url}):
                    engine=create_database_engine(url)
                    try:
                        self.assertEqual(inspect(engine).get_table_names(),[])
                        if origin:
                            command.upgrade(config,origin)
                            with Session(engine) as db:
                                user=User(email='legacy@example.com',full_name='Migration fixture',password_hash='test-only-no-login');db.add(user);db.flush()
                                building=Building(owner_id=user.id,name='Retained legacy building');db.add(building);db.flush()
                                db.execute(text("INSERT INTO predictions (building_id,source_timestamp,prediction_wh,horizon_minutes,model_name,model_checksum,created_at) VALUES (:bid,'2016-01-01 00:00:00',10,10,'legacy-fixture',:hash,'2026-01-01 00:00:00')"),{'bid':building.id,'hash':'0'*64});db.commit()
                        command.upgrade(config,'head');command.upgrade(config,'head')
                        command.current(config,verbose=True);command.heads(config,verbose=True)
                        self.assertIn('0026_prediction_feature_snapshots',stdout.getvalue())
                        with engine.connect() as db:
                            self.assertEqual(db.execute(text('PRAGMA foreign_keys')).scalar_one(),1)
                            self.assertEqual(db.execute(text('PRAGMA foreign_key_check')).all(),[])
                            self.assertEqual(db.execute(text('SELECT version_num FROM alembic_version')).all(),[('0026_prediction_feature_snapshots',)])
                            self.assertEqual(compare_metadata(MigrationContext.configure(db),Base.metadata),[])
                            self.assertIn('uq_users_email_normalized',[row[0] for row in db.execute(text("SELECT name FROM sqlite_master WHERE type='index'"))])
                            if origin:
                                self.assertEqual(tuple(db.execute(text('SELECT prediction_wh,feature_hash,feature_snapshot_json FROM predictions')).one()),(10.0,None,None))
                                self.assertEqual(db.execute(text('SELECT count(*) FROM buildings')).scalar_one(),1)
                            else:
                                for table in ['users','buildings','measurements','predictions','auth_sessions']:self.assertEqual(db.execute(text('SELECT count(*) FROM '+table)).scalar_one(),0)
                    finally:engine.dispose()
