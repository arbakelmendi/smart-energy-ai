"""Isolated SQLite migrations and invariants; fixtures are test-only, never seeds."""
from datetime import datetime, timezone
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from pydantic import ValidationError
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError, InvalidRequestError, StatementError
from sqlalchemy.orm import selectinload, sessionmaker
from sqlalchemy.schema import CreateTable

# Module collection must not depend on the developer's configured driver/URL.
# The module-level factory is unused; each test binds its own migrated file.
with patch.dict(os.environ, {'DATABASE_URL': 'sqlite:///:memory:'}):
    from backend import database
    from backend.database import Base, check_database, create_database_engine
    from backend.db_models import Building, Measurement, Prediction, RAW_MEASUREMENT_COLUMNS, User
    from backend.db_schemas import BuildingData, MeasurementData, PredictionData, UserRead

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = datetime(2016, 1, 18, 17)
# Scalar fixtures check storage rules only, never used as research or API forecasts.
VALUES = {name: 1.0 for name in RAW_MEASUREMENT_COLUMNS}


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.url = 'sqlite:///' + (Path(self.directory.name) / 'test.db').as_posix()
        self.config = Config(str(ROOT / 'alembic.ini'))
        self.environment = patch.dict(os.environ, {'DATABASE_URL': self.url})
        self.environment.start()
        command.upgrade(self.config, 'head')
        self.engine = create_database_engine(self.url)
        self.factory = sessionmaker(self.engine, expire_on_commit=False)
        self.session = self.factory()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()
        self.environment.stop()
        self.directory.cleanup()

    def user(self, email='fixture@example.invalid', **overrides):
        values = dict(email=email, password_hash='test-only-noncredential-hash', full_name='Test fixture')
        values.update(overrides)
        user = User(**values)
        self.session.add(user)
        self.session.flush()
        return user

    def building(self, **overrides):
        user = self.user()
        values = dict(owner_id=user.id, name='Isolated test building')
        values.update(overrides)
        building = Building(**values)
        self.session.add(building)
        self.session.flush()
        return building

    def prediction(self, building_id, **overrides):
        values = dict(building_id=building_id, source_timestamp=ORIGIN, prediction_wh=12.0,
                      model_name='test-only-model', model_checksum='0' * 64)
        values.update(overrides)
        return Prediction(**values)

    def test_migration_creates_exact_schema_and_is_idempotent(self):
        self.assertEqual(set(inspect(self.engine).get_table_names()), set(Base.metadata.tables) | {'alembic_version'})
        command.upgrade(self.config, 'head')
        with self.engine.connect() as connection:
            self.assertEqual(compare_metadata(MigrationContext.configure(connection), Base.metadata), [])
        self.assertEqual(check_database(self.engine), {'connected': True, 'schema_present': True,
                                                      'migration_revision': '0021_database_foundation'})

    def test_migration_downgrade_and_reupgrade(self):
        self.session.close()
        command.downgrade(self.config, 'base')
        self.assertEqual(set(inspect(self.engine).get_table_names()), {'alembic_version'})
        command.upgrade(self.config, 'head')
        self.assertTrue(check_database(self.engine)['schema_present'])

    def test_engine_creation_does_not_create_database_file(self):
        path = Path(self.directory.name) / 'not-connected.db'
        engine = create_database_engine('sqlite:///' + path.as_posix())
        try:
            self.assertFalse(path.exists())
        finally:
            engine.dispose()

    def test_no_seeded_records(self):
        for model in (User, Building, Measurement, Prediction):
            self.assertEqual(self.session.scalar(select(func.count()).select_from(model)), 0)

    def test_user_defaults_and_timestamps(self):
        user = self.user()
        self.assertEqual(user.role, 'USER')
        self.assertTrue(user.is_active)
        self.assertIsInstance(user.created_at, datetime)
        before = user.updated_at
        user.full_name = 'Updated fixture'
        self.session.flush()
        self.assertGreaterEqual(user.updated_at, before)
        self.assertIsNone(user.created_at.tzinfo)  # documented naive UTC audit time

    def test_unique_email(self):
        self.user()
        with self.assertRaises(IntegrityError):
            self.user()
        self.session.rollback()
        self.assertEqual(self.session.scalar(select(func.count()).select_from(User)), 0)
        self.user('after-rollback@example.invalid')
        self.session.commit()

    def test_roles(self):
        self.user(role='ADMIN')
        with self.assertRaises(IntegrityError):
            self.user('other@example.invalid', role='OWNER')

    def test_required_user_fields(self):
        with self.assertRaises(IntegrityError):
            self.user(password_hash=None)
        self.assertNotIn('password', User.__table__.columns)

    def test_relationships_and_explicit_loading(self):
        building = self.building()
        self.session.add(Measurement(building_id=building.id, timestamp=ORIGIN, **VALUES))
        self.session.add(self.prediction(building.id))
        self.session.commit()
        self.session.expire_all()
        with self.assertRaises(InvalidRequestError):
            _ = building.measurements
        loaded = self.session.scalar(select(Building).options(selectinload(Building.owner),
                            selectinload(Building.measurements), selectinload(Building.predictions)))
        self.assertEqual(len(loaded.measurements), 1)
        self.assertEqual(len(loaded.predictions), 1)
        owner = self.session.scalar(select(User).options(selectinload(User.buildings)))
        self.assertEqual(owner.buildings[0].id, loaded.id)
        self.assertEqual(loaded.owner.id, owner.id)

    def test_floor_area_nullable_or_positive(self):
        building = self.building(floor_area_m2=None)
        building.floor_area_m2 = 10.5
        self.session.flush()
        building.floor_area_m2 = 0
        with self.assertRaises(IntegrityError):
            self.session.flush()

    def test_negative_floor_area_rejected(self):
        with self.assertRaises(IntegrityError):
            self.building(floor_area_m2=-1)

    def test_finite_float_bind_validation(self):
        building = self.building()
        self.session.commit()
        for invalid in (float('nan'), float('inf'), float('-inf'), True, '1'):
            with self.subTest(invalid=repr(invalid)):
                building.floor_area_m2 = invalid
                with self.assertRaises(StatementError):
                    self.session.flush()
                self.session.rollback()

    def test_measurement_uniqueness_per_building(self):
        building = self.building()
        self.session.add(Measurement(building_id=building.id, timestamp=ORIGIN, **VALUES))
        self.session.flush()
        self.session.add(Measurement(building_id=building.id, timestamp=ORIGIN, **VALUES))
        with self.assertRaises(IntegrityError):
            self.session.flush()

    def test_measurement_same_time_allowed_for_other_building(self):
        first = self.building()
        second = Building(owner_id=first.owner_id, name='Second isolated fixture')
        self.session.add(second)
        self.session.flush()
        for building in (first, second):
            self.session.add(Measurement(building_id=building.id, timestamp=ORIGIN, **VALUES))
        self.session.commit()
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Measurement)), 2)

    def test_measurement_values_required(self):
        building = self.building()
        values = VALUES.copy()
        values.pop('T6')
        self.session.add(Measurement(building_id=building.id, timestamp=ORIGIN, **values))
        with self.assertRaises(IntegrityError):
            self.session.flush()

    def test_all_raw_measurement_values_finite(self):
        building = self.building()
        building_id = building.id
        self.session.commit()
        for name in RAW_MEASUREMENT_COLUMNS:
            for invalid in (float('nan'), float('inf'), float('-inf')):
                with self.subTest(column=name, value=repr(invalid)):
                    values = VALUES | {name: invalid}
                    self.session.add(Measurement(building_id=building_id, timestamp=ORIGIN, **values))
                    with self.assertRaises(StatementError):
                        self.session.flush()
                    self.session.rollback()

    def test_database_guards_direct_sql_nonfinite(self):
        building = self.building()
        prediction = self.prediction(building.id)
        self.session.add(prediction)
        self.session.commit()
        for invalid in (float('nan'), float('inf'), float('-inf')):
            for sql in ('UPDATE predictions SET prediction_wh=:value',
                        'UPDATE buildings SET floor_area_m2=:value'):
                # NULL is legitimate for optional floor area; sqlite converts NaN to NULL.
                if 'floor_area' in sql and invalid != invalid:
                    continue
                with self.subTest(sql=sql, value=repr(invalid)):
                    with self.assertRaises(IntegrityError):
                        self.session.execute(text(sql), {'value': invalid})
                    self.session.rollback()

    def test_prediction_constraints_and_snapshot(self):
        building = self.building()
        prediction = self.prediction(building.id, recommendation_level='HIGH',
                         recommendation_code='HIGH_CONSUMPTION', recommendation_priority='medium',
                         recommendation_text='Test-only snapshot')
        self.session.add(prediction)
        self.session.commit()
        self.assertEqual(prediction.horizon_minutes, 10)
        self.assertEqual(prediction.recommendation_text, 'Test-only snapshot')
        prediction.horizon_minutes = 0
        with self.assertRaises(IntegrityError):
            self.session.flush()

    def test_prediction_incomplete_snapshot_rejected(self):
        building = self.building()
        self.session.add(self.prediction(building.id, recommendation_level='HIGH'))
        with self.assertRaises(IntegrityError):
            self.session.flush()

    def test_prediction_nonfinite_rejected(self):
        building = self.building()
        building_id = building.id
        self.session.commit()
        for invalid in (float('nan'), float('inf'), float('-inf')):
            self.session.add(self.prediction(building_id, prediction_wh=invalid))
            with self.assertRaises(StatementError):
                self.session.flush()
            self.session.rollback()

    def test_foreign_keys_enforced(self):
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text('PRAGMA foreign_keys')), 1)
        with self.assertRaises(IntegrityError):
            self.session.add(Building(owner_id=999, name='Orphan fixture'))
            self.session.flush()

    def test_user_deletion_restricted_and_building_deletion_cascades(self):
        building = self.building()
        owner_id = building.owner_id
        self.session.add(Measurement(building_id=building.id, timestamp=ORIGIN, **VALUES))
        self.session.add(self.prediction(building.id))
        self.session.commit()
        with self.assertRaises(IntegrityError):
            self.session.execute(delete(User).where(User.id == owner_id))
        self.session.rollback()
        self.session.delete(building)
        self.session.commit()
        for model in (Building, Measurement, Prediction):
            self.assertEqual(self.session.scalar(select(func.count()).select_from(model)), 0)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(User)), 1)

    def test_indexes(self):
        inspector = inspect(self.engine)
        indexed = {tuple(i['column_names']) for i in inspector.get_indexes('measurements')}
        self.assertTrue({('building_id',), ('timestamp',)} <= indexed)
        unique = inspector.get_unique_constraints('measurements')
        self.assertIn(['building_id', 'timestamp'], [u['column_names'] for u in unique])
        self.assertTrue(any(i['unique'] and i['column_names'] == ['email'] for i in inspector.get_indexes('users')))

    def test_raw_contract_matches_committed_schema(self):
        schema = json.loads((ROOT / 'ml/results/feature_schema.json').read_text())
        self.assertEqual(list(RAW_MEASUREMENT_COLUMNS), schema['model_feature_columns'][:26])
        self.assertEqual(set(Measurement.__table__.columns.keys()), set(RAW_MEASUREMENT_COLUMNS) | {'id', 'building_id', 'timestamp'})

    def test_schema_never_serializes_password_hash(self):
        user = self.user()
        result = UserRead.model_validate(user).model_dump()
        self.assertNotIn('password_hash', result)
        self.assertNotIn('password_hash', UserRead.model_json_schema()['properties'])
        self.assertNotIn('password', UserRead.model_fields)

    def test_application_schemas_reject_nonfinite_and_extra_inputs(self):
        for name in RAW_MEASUREMENT_COLUMNS:
            with self.assertRaises(ValidationError):
                MeasurementData(building_id=1, timestamp=ORIGIN, **(VALUES | {name: float('inf')}))
        for invalid in (float('nan'), float('inf'), float('-inf')):
            with self.assertRaises(ValidationError):
                BuildingData(owner_id=1, name='fixture', floor_area_m2=invalid)
            with self.assertRaises(ValidationError):
                PredictionData(building_id=1, source_timestamp=ORIGIN, prediction_wh=invalid,
                               model_name='fixture', model_checksum='0'*64)
        with self.assertRaises(ValidationError):
            MeasurementData(building_id=1, timestamp=ORIGIN, **VALUES, rv1=1)
        with self.assertRaises(ValidationError):
            MeasurementData(building_id=1, timestamp=ORIGIN.replace(tzinfo=timezone.utc), **VALUES)

    def test_session_dependency_rolls_back_failure_and_uncommitted_success(self):
        for fail in (False, True):
            with patch.object(database, 'SessionLocal', self.factory):
                dependency = database.get_db()
                session = next(dependency)
                session.add(User(email='rollback@example.invalid', password_hash='test-only-hash', full_name='fixture'))
                session.flush()
                if fail:
                    with self.assertRaises(RuntimeError):
                        dependency.throw(RuntimeError('controlled test failure'))
                else:
                    with self.assertRaises(StopIteration):
                        next(dependency)
            self.assertEqual(self.session.scalar(select(func.count()).select_from(User)), 0)

    def test_default_path_is_repo_relative_not_cwd(self):
        self.assertEqual(database.database_url('sqlite:///./smartenergy.db').database,
                         str(ROOT / 'smartenergy.db'))
        url = database.database_url('postgresql+psycopg://example.invalid/example')
        self.assertEqual(url.drivername, 'postgresql+psycopg')

    def test_postgresql_offline_migration_compiles_without_driver(self):
        output = StringIO()
        config = Config(str(ROOT / 'alembic.ini'), output_buffer=output)
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql+psycopg://example.invalid/example'}):
            command.upgrade(config, 'head', sql=True)
        ddl = output.getvalue()
        self.assertIn('CREATE TABLE measurements', ddl)
        self.assertIn('CREATE TABLE predictions', ddl)
        self.assertNotIn('is_active IN (0, 1)', ddl)
        for table in Base.metadata.sorted_tables:
            self.assertTrue(str(CreateTable(table).compile(dialect=postgresql.dialect())))


if __name__ == '__main__':
    unittest.main()
