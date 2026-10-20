"""Independent relational foundation. Importing never connects or creates tables."""
from collections.abc import Generator
import os
from pathlib import Path

from sqlalchemy import MetaData, create_engine, event, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = "sqlite:///./smartenergy.db"


def database_url(value: str | None = None):
    """Resolve relative SQLite files against repository root, not process cwd."""
    url = make_url(value if value is not None else os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))
    if url.get_backend_name() == "sqlite" and url.database not in (None, "", ":memory:"):
        if not Path(url.database).is_absolute():
            url = url.set(database=str(ROOT / url.database))
    return url


def create_database_engine(url: str | None = None) -> Engine:
    resolved = database_url(url)
    options = {"pool_pre_ping": True, "hide_parameters": True}
    if resolved.get_backend_name() == "sqlite":
        options["connect_args"] = {"check_same_thread": False, "timeout": 10}
    engine = create_engine(resolved, **options)
    if resolved.get_backend_name() == "sqlite":
        @event.listens_for(engine, "connect")
        def sqlite_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })


engine = create_database_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """One session per request; caller commits explicitly, failures roll back."""
    with SessionLocal() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        # close() rolls back any uncommitted transaction on normal exit too.


def check_database(db_engine: Engine) -> dict:
    """Explicit internal probe, never invoked by existing research health routes.

    Takes an engine explicitly so tests cannot accidentally probe developer data.
    Connection errors propagate to the caller; never log a credential-bearing URL.
    """
    with db_engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        tables = set(inspect(connection).get_table_names())
        revision = (connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
                    if "alembic_version" in tables else None)
    return {"connected": True, "schema_present": {"users", "buildings", "measurements", "predictions"} <= tables,
            "migration_revision": revision}
