"""Real auth handlers against migrated disposable SQLite; runtime-only credentials."""
from datetime import timedelta
import os
from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend import auth
from backend.auth_schemas import normalize_email
from backend.database import create_database_engine, get_db
from backend.db_models import AuthSession, User, utc_now
from backend.main import app
from scripts.create_admin import create_admin

ROOT = Path(__file__).resolve().parents[1]


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.url = 'sqlite:///' + (Path(self.directory.name) / 'auth.db').as_posix()
        self.env = patch.dict(os.environ, {'DATABASE_URL': self.url, 'SMARTENERGY_COOKIE_SECURE': 'false', 'SMARTENERGY_SESSION_HOURS': '24'})
        self.env.start()
        self.config = Config(str(ROOT / 'alembic.ini'))
        command.upgrade(self.config, 'head')
        self.engine = create_database_engine(self.url)
        self.factory = sessionmaker(self.engine, expire_on_commit=False)
        def isolated_db():
            with self.factory() as db:
                yield db
        self.dependency = isolated_db
        self.previous = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = isolated_db
        self.client = TestClient(app, base_url='http://localhost', headers={'X-SmartEnergy-CSRF': '1'})
        self.password = secrets.token_urlsafe(20)
        self.email = 'auth-' + secrets.token_hex(8) + '@example.com'

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        self.engine.dispose()
        self.env.stop()
        self.directory.cleanup()

    def signup(self, **values):
        body = dict(email=self.email, full_name='Authentication fixture', password=self.password)
        body.update(values)
        return self.client.post('/auth/signup', json=body)

    def login(self, **values):
        return self.client.post('/auth/login', json=dict(email=self.email, password=self.password) | values)

    def test_password_hash_is_argon2id_salted_and_verifies(self):
        first = auth.hash_password(self.password)
        second = auth.hash_password(self.password)
        self.assertTrue(first.startswith('$argon2id$'))
        self.assertNotEqual(first, self.password)
        self.assertNotEqual(first, second)
        self.assertTrue(auth.verify_password(self.password, first))
        self.assertFalse(auth.verify_password(self.password + 'wrong', first))
        self.assertFalse(auth.verify_password(self.password, 'not-a-password-hash'))

    def test_signup_normalizes_and_establishes_session(self):
        response = self.signup(email='  ' + self.email.upper() + '  ')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['email'], self.email)
        self.assertEqual(response.json()['role'], 'USER')
        self.assertEqual(self.client.get('/auth/me').status_code, 200)
        with self.factory() as db:
            user = db.scalar(select(User))
            self.assertTrue(user.password_hash.startswith('$argon2id$'))
            self.assertNotEqual(user.password_hash, self.password)

    def test_duplicate_case_signup(self):
        self.assertEqual(self.signup().status_code, 201)
        self.assertEqual(self.signup(email=self.email.upper()).status_code, 409)

    def test_database_index_rejects_case_variation(self):
        self.signup()
        with self.factory() as db:
            db.add(User(email=self.email.upper(), password_hash='test-only-hash', full_name='duplicate'))
            with self.assertRaises(IntegrityError):
                db.commit()
        with self.engine.connect() as db:
            self.assertIn('lower(trim(email))', db.scalar(text("SELECT sql FROM sqlite_master WHERE name='uq_users_email_normalized'")))

    def test_public_signup_cannot_request_admin(self):
        self.assertEqual(self.signup(role='ADMIN').status_code, 422)
        with self.factory() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(User)), 0)

    def test_signup_validation(self):
        for values in ({'password': 'short'}, {'password': 'x'*129}, {'email': 'invalid'}, {'full_name': '  '}):
            with self.subTest(fields=list(values)):
                self.assertEqual(self.signup(**values).status_code, 422)

    def test_full_name_not_silently_normalized(self):
        response = self.signup(full_name='  Actual spelling  ')
        self.assertEqual(response.json()['full_name'], '  Actual spelling  ')

    def test_login_normalized_identity(self):
        self.signup()
        self.client.post('/auth/logout')
        self.assertEqual(self.login(email=' '+self.email.upper()+' ').status_code, 200)
        self.assertEqual(self.client.get('/auth/me').json()['email'], self.email)

    def test_generic_wrong_unknown_and_inactive_login(self):
        self.signup()
        wrong = self.login(password=self.password + 'wrong')
        unknown = self.login(email='absent-'+secrets.token_hex(8)+'@example.com')
        with self.factory() as db:
            user = db.scalar(select(User))
            user.is_active = False
            db.commit()
        inactive = self.login()
        self.assertEqual([wrong.status_code, unknown.status_code, inactive.status_code], [401]*3)
        self.assertEqual(wrong.json(), unknown.json())
        self.assertEqual(wrong.json(), inactive.json())

    def test_raw_token_only_cookie_hash_in_database(self):
        response = self.signup()
        token = self.client.cookies.get(auth.COOKIE_NAME)
        self.assertEqual(len(token), 43)
        with self.factory() as db:
            row = db.scalar(select(AuthSession))
            self.assertEqual(row.token_hash, auth.token_digest(token))
            self.assertNotEqual(row.token_hash, token)
            self.assertGreater(row.expires_at, row.created_at)
        for result in (response, self.client.get('/auth/me')):
            self.assertEqual(set(result.json()), {'id','email','full_name','role','is_active'})
            for secret in (token, auth.token_digest(token), self.password, 'password_hash', 'token_hash'):
                self.assertNotIn(secret, result.text)
            self.assertEqual(result.headers['cache-control'], 'no-store')

    def test_cookie_policy_and_configurable_lifetime(self):
        with patch.dict(os.environ, {'SMARTENERGY_SESSION_HOURS': '2'}):
            response = self.signup()
        cookie = response.headers['set-cookie'].lower()
        for value in ('httponly', 'samesite=lax', 'path=/', 'max-age=7200'):
            self.assertIn(value, cookie)
        self.assertNotIn('secure;', cookie)
        with self.factory() as db:
            row = db.scalar(select(AuthSession))
            self.assertEqual(row.expires_at - row.created_at, timedelta(hours=2))

    def test_secure_cookie_in_https_configuration(self):
        with patch.dict(os.environ, {'SMARTENERGY_COOKIE_SECURE': 'true'}):
            response = self.signup()
        self.assertIn('secure', response.headers['set-cookie'].lower())

    def test_me_unauthenticated_or_malformed(self):
        self.assertEqual(self.client.get('/auth/me').status_code, 401)
        self.client.cookies.set(auth.COOKIE_NAME, 'malformed')
        response = self.client.get('/auth/me')
        self.assertEqual(response.status_code, 401)
        self.assertIn('max-age=0', response.headers['set-cookie'].lower())

    def test_session_survives_new_client(self):
        self.signup()
        with TestClient(app, base_url='http://localhost', cookies=self.client.cookies) as other:
            self.assertEqual(other.get('/auth/me').status_code, 200)

    def test_logout_revokes_and_is_idempotent(self):
        self.signup()
        token = self.client.cookies.get(auth.COOKIE_NAME)
        self.assertEqual(self.client.post('/auth/logout').status_code, 200)
        self.assertEqual(self.client.get('/auth/me').status_code, 401)
        self.client.cookies.set(auth.COOKIE_NAME, token)
        self.assertEqual(self.client.get('/auth/me').status_code, 401)
        self.assertEqual(self.client.post('/auth/logout').status_code, 200)
        with self.factory() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(AuthSession)), 0)

    def test_expiration_boundary_rejects_and_deletes(self):
        self.signup()
        with self.factory() as db:
            expiry = db.scalar(select(AuthSession)).expires_at
        with patch.object(auth, 'utc_now', return_value=expiry):
            response = self.client.get('/auth/me')
        self.assertEqual(response.status_code, 401)
        self.assertIn('max-age=0', response.headers['set-cookie'].lower())
        with self.factory() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(AuthSession)), 0)

    def test_revoked_session(self):
        self.signup()
        with self.factory() as db:
            db.execute(delete(AuthSession))
            db.commit()
        self.assertEqual(self.client.get('/auth/me').status_code, 401)

    def test_inactive_existing_session_revokes_all_user_sessions(self):
        self.signup()
        self.login()
        with self.factory() as db:
            user = db.scalar(select(User))
            user.is_active = False
            db.commit()
        self.assertEqual(self.client.get('/auth/me').status_code, 401)
        with self.factory() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(AuthSession)), 0)

    def test_login_rotates_current_session(self):
        self.signup()
        original = self.client.cookies.get(auth.COOKIE_NAME)
        self.login()
        self.assertNotEqual(original, self.client.cookies.get(auth.COOKIE_NAME))
        with self.factory() as db:
            self.assertIsNone(db.scalar(select(AuthSession).where(AuthSession.token_hash == auth.token_digest(original))))

    def test_require_admin_uses_backend_role(self):
        self.signup()
        probe = FastAPI()
        probe.dependency_overrides[get_db] = self.dependency
        @probe.get('/admin-probe')
        def admin_probe(user=Depends(auth.require_admin)):
            return {'role': user.role}
        with TestClient(probe, base_url='http://localhost', cookies=self.client.cookies) as client:
            self.assertEqual(client.get('/admin-probe').status_code, 403)
            with self.factory() as db:
                user = db.scalar(select(User))
                user.role = 'ADMIN'
                db.commit()
            self.assertEqual(client.get('/admin-probe').json(), {'role':'ADMIN'})
        with TestClient(probe, base_url='http://localhost') as client:
            self.assertEqual(client.get('/admin-probe').status_code, 401)

    def test_admin_bootstrap_hashes_and_refuses_promotion(self):
        with self.factory() as db:
            user = create_admin(self.email, 'Admin fixture', self.password, db)
            self.assertEqual(user.role, 'ADMIN')
            self.assertTrue(auth.verify_password(self.password, user.password_hash))
            with self.assertRaises(ValueError):
                create_admin(self.email.upper(), 'Other', self.password, db)
        self.assertEqual(self.login().json()['role'], 'ADMIN')

    def test_bootstrap_never_promotes_existing_user(self):
        self.signup()
        with self.factory() as db:
            with self.assertRaises(ValueError):
                create_admin(self.email.upper(), 'Attempted promotion', self.password, db)
            self.assertEqual(db.scalar(select(User)).role, 'USER')

    def test_admin_cli_uses_hidden_confirmation_prompts(self):
        from scripts import create_admin as cli
        from contextlib import redirect_stdout
        from io import StringIO
        with patch.object(cli, 'SessionLocal', self.factory), patch('builtins.input', side_effect=[self.email,'Prompt fixture']), patch.object(cli, 'getpass', side_effect=[self.password,self.password]) as prompt, redirect_stdout(StringIO()):
            cli.main()
        self.assertEqual(prompt.call_count, 2)
        with self.factory() as db:
            user=db.scalar(select(User))
            self.assertEqual(user.role,'ADMIN')
            self.assertTrue(auth.verify_password(self.password,user.password_hash))

    def test_user_deletion_cascades_sessions(self):
        self.signup()
        with self.factory() as db:
            db.execute(delete(User))
            db.commit()
            self.assertEqual(db.scalar(select(func.count()).select_from(AuthSession)),0)
        self.assertEqual(self.client.get('/auth/me').status_code,401)

    def test_csrf_origin_and_header_enforced(self):
        body = dict(email=self.email, password=self.password, full_name='fixture')
        self.assertEqual(self.client.post('/auth/signup', json=body, headers={'Origin':'https://untrusted.example'}).status_code, 403)
        with TestClient(app, base_url='http://localhost') as client:
            self.assertEqual(client.post('/auth/signup', json=body).status_code, 403)
            self.assertEqual(client.post('/auth/logout').status_code, 403)
        self.assertEqual(self.client.post('/auth/signup', json=body, headers={'Origin':'http://localhost:5173'}).status_code, 201)

    def test_credentialed_cors_preflight(self):
        headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Content-Type,X-SmartEnergy-CSRF'}
        response=self.client.options('/auth/login',headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['access-control-allow-credentials'], 'true')
        self.assertEqual(response.headers['access-control-allow-origin'], headers['Origin'])

    def test_phase21_upgrade_normalizes_without_losing_ownership(self):
        self.engine.dispose()
        command.downgrade(self.config, '0021_database_foundation')
        with self.engine.begin() as connection:
            now=utc_now().isoformat(sep=" ")
            connection.execute(text('INSERT INTO users (email,password_hash,full_name,created_at,updated_at) VALUES (:email,:hash,:name,:now,:now)'),
              {'email':' '+self.email.upper()+' ','hash':'test-only-legacy-hash','name':'Legacy fixture','now':now})
            connection.execute(text('INSERT INTO buildings (owner_id,name,created_at,updated_at) VALUES (1,:name,:now,:now)'),{'name':'Legacy ownership fixture','now':now})
        command.upgrade(self.config, 'head')
        with self.factory() as db:
            self.assertEqual(db.scalar(select(User)).email, self.email)
            self.assertEqual(db.scalar(text('SELECT owner_id FROM buildings')), 1)

    def test_migration_duplicate_normalization_fails_without_automatic_merge(self):
        self.engine.dispose()
        command.downgrade(self.config, '0021_database_foundation')
        with self.engine.begin() as connection:
            for value in (self.email, self.email.upper()):
                connection.execute(text('INSERT INTO users (email,password_hash,full_name,created_at,updated_at) VALUES (:email,:hash,:name,:now,:now)'),
                                  {'email':value,'hash':'test-only-hash','name':'Legacy fixture','now':utc_now().isoformat(sep=' ')})
        with self.assertRaisesRegex(RuntimeError, 'collide'):
            command.upgrade(self.config, 'head')
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text('SELECT count(*) FROM users')), 2)

    def test_idn_normalization_and_invalid_email(self):
        self.assertEqual(normalize_email(' USER@EXAMPLE.COM '), 'user@example.com')
        self.assertTrue(normalize_email('user@b\u00fccher.de').endswith('@xn--bcher-kva.de'))
        with self.assertRaises(ValueError):
            normalize_email('not an email')


if __name__ == '__main__':
    unittest.main()
