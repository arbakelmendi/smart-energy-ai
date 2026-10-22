"""Explicit local, active-ADMIN-owned reference import. Never runs at startup."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from backend.database import ROOT, SessionLocal
from backend.db_models import User, Building, Measurement
from backend.measurement_service import MAX_BYTES, parse_csv, persist_rows

REFERENCE_NAME = "UCI Reference Building"
REFERENCE_DESCRIPTION = ("UCI Appliances Energy Prediction dataset; reference research data, not live operational data. "
    "The final ML model was developed and validated on this dataset. Original timezone-naive timestamps are preserved.")


def import_reference(db, admin_email, source=None):
    admin = db.scalar(select(User).where(func.lower(func.trim(User.email)) == admin_email.strip().lower(),
        User.role == "ADMIN", User.is_active.is_(True)))
    if admin is None:
        raise ValueError("Select an existing active ADMIN account")
    # Reserved name plus exact provenance description is the reference identity for this owner's local utility.
    matches = db.scalars(select(Building).where(Building.owner_id == admin.id, Building.name == REFERENCE_NAME)).all()
    if len(matches) > 1 or (matches and matches[0].description != REFERENCE_DESCRIPTION):
        raise ValueError("Ambiguous reference building name; no building was changed")
    building = matches[0] if matches else None
    if building is not None and db.scalar(select(Measurement.id).where(Measurement.building_id == building.id).limit(1)):
        raise ValueError("Reference history already exists; repeat import rejected without changes")
    source = Path(source) if source else ROOT / "data/raw/energydata_complete.csv"
    with source.open("rb") as stream:
        rows, ignored = parse_csv(stream.read(MAX_BYTES + 1))
    try:
        if building is None:
            building = Building(owner_id=admin.id, name=REFERENCE_NAME, description=REFERENCE_DESCRIPTION)
            db.add(building)
            db.flush()
        result = persist_rows(db, building.id, rows, ignored)
    except Exception:
        db.rollback()
        raise
    return {**result, "reference_name": REFERENCE_NAME}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-email", required=True, help="Existing active administrator; never promotes accounts")
    args = parser.parse_args()
    try:
        with SessionLocal() as db:
            result = import_reference(db, args.admin_email)
        print(json.dumps(result, default=str))
    except (ValueError, OSError, HTTPException, SQLAlchemyError):
        print("Reference import rejected. Verify active ADMIN, migrations, local CSV and reference-name/history conflicts. Nothing partially imported.", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
