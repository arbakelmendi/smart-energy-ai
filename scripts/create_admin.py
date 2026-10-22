"""Explicit local bootstrap; never accepts password command-line arguments."""
from getpass import getpass, GetPassWarning
import warnings
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from backend.auth import hash_password
from backend.auth_schemas import SignupRequest
from backend.database import SessionLocal
from backend.db_models import User


def create_admin(email, full_name, password, db):
    body = SignupRequest(email=email, full_name=full_name, password=password)
    if db.scalar(select(User.id).where(func.lower(func.trim(User.email)) == body.email)) is not None:
        raise ValueError("Account already exists; no automatic promotion or overwrite is permitted")
    user = User(email=body.email, full_name=body.full_name,
                password_hash=hash_password(body.password.get_secret_value()), role="ADMIN", is_active=True)
    try:
        db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Account already exists; no account was changed") from None
    return user


def main():
    email = input("Administrator email: ")
    name = input("Full name: ")
    with warnings.catch_warnings():
        warnings.simplefilter("error", GetPassWarning)
        password = getpass("Password (12-128 characters): ")
        if password != getpass("Confirm password: "):
            raise ValueError("Passwords do not match")
    with SessionLocal() as db:
        create_admin(email, name, password, db)
    print("Administrator created. Sign in through the application.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, SQLAlchemyError, GetPassWarning):
        print("Administrator not created. Check validated input, duplicate accounts and database migrations. No existing account is promoted.", file=sys.stderr)
        raise SystemExit(1)
