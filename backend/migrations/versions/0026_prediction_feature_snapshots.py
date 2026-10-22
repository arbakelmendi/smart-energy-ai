"""Audit model inputs and enforce fingerprint-aware forecast idempotency.

Legacy rows remain unchanged with NULL snapshot/hash; no deduplication or guesses.
"""
from alembic import op
import sqlalchemy as sa

revision = "0026_prediction_feature_snapshots"
down_revision = "0022_authentication_sessions"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("predictions") as batch:
        batch.add_column(sa.Column("feature_hash", sa.String(64), nullable=True))
        batch.add_column(sa.Column("feature_snapshot_json", sa.Text(), nullable=True))
        batch.create_check_constraint(op.f("ck_predictions_complete_feature_snapshot"),
            "(feature_hash IS NULL AND feature_snapshot_json IS NULL) OR (feature_hash IS NOT NULL AND length(feature_hash) = 64 AND feature_snapshot_json IS NOT NULL)")
        batch.create_unique_constraint("uq_predictions_input", ["building_id", "source_timestamp", "model_checksum", "feature_hash"])


def downgrade():
    with op.batch_alter_table("predictions") as batch:
        batch.drop_constraint("uq_predictions_input", type_="unique")
        batch.drop_constraint(op.f("ck_predictions_complete_feature_snapshot"), type_="check")
        batch.drop_column("feature_snapshot_json")
        batch.drop_column("feature_hash")
