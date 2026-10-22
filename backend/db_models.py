"""Phase21 ORM schema only: no account behavior, seeds, imports or forecasting."""
from datetime import datetime, timezone
import math
from numbers import Real

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from .database import Base

RAW_MEASUREMENT_COLUMNS = ('Appliances', 'lights', 'T1', 'RH_1', 'T2', 'RH_2', 'T3', 'RH_3', 'T4', 'RH_4', 'T5', 'RH_5', 'T6', 'RH_6', 'T7', 'RH_7', 'T8', 'RH_8', 'T9', 'RH_9', 'T_out', 'Press_mm_hg', 'RH_out', 'Windspeed', 'Visibility', 'Tdewpoint')
MAX_FINITE = "1.7976931348623157e308"


class FiniteFloat(TypeDecorator):
    """Reject bool, numeric strings, NaN and infinities on ORM/Core bound writes."""
    impl = Float
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
            raise ValueError("Expected a finite real numeric value")
        return float(value)


def finite_check(column, name=None):
    return CheckConstraint(f'"{column}" >= -{MAX_FINITE} AND "{column}" <= {MAX_FINITE}',
                           name=name or column.lower() + "_finite")


def utc_now():
    # Audit timestamps stored as naive UTC consistently across SQLite/PostgreSQL.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AuditTimestamps:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class User(AuditTimestamps, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('USER', 'ADMIN')", name="valid_role"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(5), default="USER", server_default="USER")
    is_active: Mapped[bool] = mapped_column(Boolean(create_constraint=True, name="active_boolean"), default=True, server_default="1")
    auth_sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user", lazy="raise", cascade="all, delete-orphan", passive_deletes=True)
    buildings: Mapped[list["Building"]] = relationship(back_populates="owner", lazy="raise", passive_deletes="all")


# Database-level ASCII canonical identity uniqueness, including direct SQL writes.
Index("uq_users_email_normalized", func.lower(func.trim(User.email)), unique=True)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (CheckConstraint("length(token_hash) = 64", name="hash_length"),
                      CheckConstraint("expires_at > created_at", name="valid_lifetime"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    user: Mapped[User] = relationship(back_populates="auth_sessions", lazy="raise")


class Building(AuditTimestamps, Base):
    __tablename__ = "buildings"
    __table_args__ = (CheckConstraint("floor_area_m2 > 0", name="positive_floor_area"), finite_check("floor_area_m2"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    building_type: Mapped[str | None] = mapped_column(String(100))
    floor_area_m2: Mapped[float | None] = mapped_column(FiniteFloat)
    city: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[User] = relationship(back_populates="buildings", lazy="raise")
    measurements: Mapped[list["Measurement"]] = relationship(back_populates="building", lazy="raise", cascade="all, delete-orphan", passive_deletes=True)
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="building", lazy="raise", cascade="all, delete-orphan", passive_deletes=True)


class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (UniqueConstraint("building_id", "timestamp", name="uq_measurements_building_timestamp"),
                      *(finite_check(name) for name in RAW_MEASUREMENT_COLUMNS))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id", ondelete="CASCADE"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    Appliances: Mapped[float] = mapped_column(FiniteFloat)
    lights: Mapped[float] = mapped_column(FiniteFloat)
    T1: Mapped[float] = mapped_column(FiniteFloat)
    RH_1: Mapped[float] = mapped_column(FiniteFloat)
    T2: Mapped[float] = mapped_column(FiniteFloat)
    RH_2: Mapped[float] = mapped_column(FiniteFloat)
    T3: Mapped[float] = mapped_column(FiniteFloat)
    RH_3: Mapped[float] = mapped_column(FiniteFloat)
    T4: Mapped[float] = mapped_column(FiniteFloat)
    RH_4: Mapped[float] = mapped_column(FiniteFloat)
    T5: Mapped[float] = mapped_column(FiniteFloat)
    RH_5: Mapped[float] = mapped_column(FiniteFloat)
    T6: Mapped[float] = mapped_column(FiniteFloat)
    RH_6: Mapped[float] = mapped_column(FiniteFloat)
    T7: Mapped[float] = mapped_column(FiniteFloat)
    RH_7: Mapped[float] = mapped_column(FiniteFloat)
    T8: Mapped[float] = mapped_column(FiniteFloat)
    RH_8: Mapped[float] = mapped_column(FiniteFloat)
    T9: Mapped[float] = mapped_column(FiniteFloat)
    RH_9: Mapped[float] = mapped_column(FiniteFloat)
    T_out: Mapped[float] = mapped_column(FiniteFloat)
    Press_mm_hg: Mapped[float] = mapped_column(FiniteFloat)
    RH_out: Mapped[float] = mapped_column(FiniteFloat)
    Windspeed: Mapped[float] = mapped_column(FiniteFloat)
    Visibility: Mapped[float] = mapped_column(FiniteFloat)
    Tdewpoint: Mapped[float] = mapped_column(FiniteFloat)
    building: Mapped[Building] = relationship(back_populates="measurements", lazy="raise")


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("building_id", "source_timestamp", "model_checksum", "feature_hash", name="uq_predictions_input"),
        CheckConstraint("(feature_hash IS NULL AND feature_snapshot_json IS NULL) OR (feature_hash IS NOT NULL AND length(feature_hash) = 64 AND feature_snapshot_json IS NOT NULL)", name="complete_feature_snapshot"),
        finite_check("prediction_wh"),
        CheckConstraint("horizon_minutes > 0", name="positive_horizon"),
        CheckConstraint("recommendation_level IN ('NORMAL', 'ELEVATED', 'HIGH', 'VERY HIGH')", name="valid_recommendation_level"),
        CheckConstraint("recommendation_priority IN ('low', 'medium', 'high')", name="valid_recommendation_priority"),
        CheckConstraint("length(model_checksum) = 64", name="checksum_length"),
        CheckConstraint("(recommendation_level IS NULL AND recommendation_code IS NULL AND recommendation_priority IS NULL AND recommendation_text IS NULL) OR (recommendation_level IS NOT NULL AND recommendation_code IS NOT NULL AND recommendation_priority IS NOT NULL AND recommendation_text IS NOT NULL)", name="complete_recommendation"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id", ondelete="CASCADE"), index=True)
    source_timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    prediction_wh: Mapped[float] = mapped_column(FiniteFloat)
    horizon_minutes: Mapped[int] = mapped_column(Integer, default=10, server_default="10")
    model_name: Mapped[str] = mapped_column(String(200))
    model_checksum: Mapped[str] = mapped_column(String(64))
    # Nullable only to preserve legacy records; Phase26 always supplies both fields.
    feature_hash: Mapped[str | None] = mapped_column(String(64))
    feature_snapshot_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    recommendation_level: Mapped[str | None] = mapped_column(String(20))
    recommendation_code: Mapped[str | None] = mapped_column(String(100))
    recommendation_priority: Mapped[str | None] = mapped_column(String(10))
    recommendation_text: Mapped[str | None] = mapped_column(Text)
    building: Mapped[Building] = relationship(back_populates="predictions", lazy="raise")
