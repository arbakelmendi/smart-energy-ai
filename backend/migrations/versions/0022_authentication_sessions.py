"""Normalize account identities and add hashed opaque sessions.

Revision ID: 0022_authentication_sessions
Revises: 0021_database_foundation
"""
from alembic import context, op
import sqlalchemy as sa
from email_validator import validate_email, EmailNotValidError

revision = "0022_authentication_sessions"
down_revision = "0021_database_foundation"
branch_labels = None
depends_on = None


def upgrade():
    if context.is_offline_mode():
        # Offline SQL requires legacy identities to be prevalidated/normalized.
        op.execute("UPDATE users SET email = lower(trim(email))")
    else:
        connection = op.get_bind()
        rows = connection.execute(sa.text("SELECT id, email FROM users")).all()
        normalized = []
        seen = set()
        for user_id, email in rows:
            try:
                canonical = validate_email(email.strip(), check_deliverability=False, allow_smtputf8=False).ascii_email.lower()
            except EmailNotValidError:
                raise RuntimeError("Existing user email is invalid; correct legacy identities explicitly before migration") from None
            if canonical in seen:
                raise RuntimeError("Existing user emails collide after normalization; resolve accounts explicitly before migration")
            seen.add(canonical)
            normalized.append((user_id, canonical))
        for user_id, email in normalized:
            connection.execute(sa.text("UPDATE users SET email=:email WHERE id=:id"), {"email": email, "id": user_id})
    op.create_index("uq_users_email_normalized", "users", [sa.text("lower(trim(email))")], unique=True)
    op.create_table("auth_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_auth_sessions"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_auth_sessions_user_id_users"),
        sa.CheckConstraint("length(token_hash) = 64", name=op.f("ck_auth_sessions_hash_length")),
        sa.CheckConstraint("expires_at > created_at", name=op.f("ck_auth_sessions_valid_lifetime")))
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])


def downgrade():
    op.drop_table("auth_sessions")
    op.drop_index("uq_users_email_normalized", table_name="users")
    # Normalized emails remain normalized; downgrade must not invent old spelling.
