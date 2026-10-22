"""Bounded CSV validation and atomic database persistence, independent of ML."""
import csv
import io
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select, func, insert
from sqlalchemy.exc import IntegrityError
from .db_models import Measurement, RAW_MEASUREMENT_COLUMNS
from .measurement_schemas import MeasurementCreate

MAX_BYTES = 16 * 1024 * 1024
MAX_ROWS = 25000
BATCH_SIZE = 500


def invalid(message, row=None, field=None):
    raise HTTPException(422, detail=[{"msg": message, "row": row, "field": field}])


def parse_csv(data: bytes):
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "CSV exceeds 16 MiB limit")
    try:
        reader = csv.reader(io.StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
        headers = next(reader, None)
        if not headers or len(headers) != len(set(headers)):
            invalid("CSV header is missing or contains duplicate columns")
        time_fields = set(headers) & {"date", "timestamp"}
        if len(time_fields) != 1:
            invalid("Provide exactly one timestamp column: date or timestamp")
        time_field = next(iter(time_fields))
        required = set(RAW_MEASUREMENT_COLUMNS) | {time_field}
        missing = required - set(headers)
        extras = set(headers) - required - {"rv1", "rv2"}
        if missing:
            invalid("Missing required columns: " + ", ".join(sorted(missing)))
        if extras:
            invalid("Unsupported columns: " + ", ".join(sorted(extras)))
        rows = []
        timestamps = set()
        for number, values in enumerate(reader, 2):
            if len(rows) >= MAX_ROWS:
                invalid("CSV exceeds 25000 measurement limit", number)
            if len(values) != len(headers):
                invalid("Malformed CSV row: column count differs from header", number)
            record = dict(zip(headers, values))
            body = {"timestamp": record[time_field]}
            for field in RAW_MEASUREMENT_COLUMNS:
                try:
                    body[field] = float(record[field])
                except (ValueError, OverflowError):
                    invalid("Expected a finite numeric value", number, field)
            try:
                row = MeasurementCreate.model_validate(body).model_dump()
            except ValidationError as exc:
                error = exc.errors()[0]
                invalid(error["msg"], number, str(error["loc"][0]))
            if row["timestamp"] in timestamps:
                invalid("Duplicate timestamp inside CSV", number, time_field)
            timestamps.add(row["timestamp"])
            rows.append(row)
        if not rows:
            invalid("CSV must contain at least one measurement")
        return rows, sorted(set(headers) & {"rv1", "rv2"})
    except (UnicodeDecodeError, csv.Error):
        invalid("CSV must be well-formed UTF-8 text")


def persist_rows(db, building_id, rows, ignored_columns=()):
    # Check existing rows in bounded queries; the unique constraint also closes races.
    stamps = [r["timestamp"] for r in rows]
    for start in range(0, len(stamps), BATCH_SIZE):
        if db.scalar(select(Measurement.id).where(Measurement.building_id == building_id,
                Measurement.timestamp.in_(stamps[start:start+BATCH_SIZE])).limit(1)) is not None:
            raise HTTPException(409, "A measurement already exists at an imported timestamp; nothing imported")
    try:
        for start in range(0, len(rows), BATCH_SIZE):
            db.execute(insert(Measurement), [{"building_id": building_id, **r} for r in rows[start:start+BATCH_SIZE]])
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Measurement conflict; nothing imported") from None
    return {"building_id": building_id, "rows_received": len(rows), "rows_imported": len(rows),
            "first_timestamp": min(stamps), "last_timestamp": max(stamps), "ignored_columns": list(ignored_columns)}


def create_measurement(db, building_id, body):
    stamp = body.timestamp
    persist_rows(db, building_id, [body.model_dump()])
    return db.scalar(select(Measurement).where(Measurement.building_id == building_id, Measurement.timestamp == stamp))


def list_measurements(db, building_id, limit, offset):
    total, first, last = db.execute(select(func.count(Measurement.id), func.min(Measurement.timestamp),
        func.max(Measurement.timestamp)).where(Measurement.building_id == building_id)).one()
    items = db.scalars(select(Measurement).where(Measurement.building_id == building_id)
        .order_by(Measurement.timestamp.desc(), Measurement.id.desc()).limit(limit).offset(offset)).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset,
            "first_timestamp": first, "last_timestamp": last}


def delete_measurement(db, building_id, measurement_id):
    row = db.scalar(select(Measurement).where(Measurement.building_id == building_id, Measurement.id == measurement_id))
    if row is None:
        raise HTTPException(404, "Measurement not found")
    db.delete(row)
    db.commit()
