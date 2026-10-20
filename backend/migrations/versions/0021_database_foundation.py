"""Initial Phase21 application schema; frozen SQL types, no research changes.

Revision ID: 0021_database_foundation
Revises: None
"""
from alembic import op
import sqlalchemy as sa

revision = '0021_database_foundation'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=200), nullable=False),
    sa.Column('role', sa.String(length=5), server_default='USER', nullable=False),
    sa.Column('is_active', sa.Boolean(create_constraint=True, name=op.f('ck_users_active_boolean')), server_default='1', nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("role IN ('USER', 'ADMIN')", name=op.f('ck_users_valid_role')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('buildings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('building_type', sa.String(length=100), nullable=True),
    sa.Column('floor_area_m2', sa.Float(), nullable=True),
    sa.Column('city', sa.String(length=200), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('"floor_area_m2" >= -1.7976931348623157e308 AND "floor_area_m2" <= 1.7976931348623157e308', name=op.f('ck_buildings_floor_area_m2_finite')),
    sa.CheckConstraint('floor_area_m2 > 0', name=op.f('ck_buildings_positive_floor_area')),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], name=op.f('fk_buildings_owner_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_buildings'))
    )
    op.create_index(op.f('ix_buildings_owner_id'), 'buildings', ['owner_id'], unique=False)
    op.create_table('measurements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('building_id', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('Appliances', sa.Float(), nullable=False),
    sa.Column('lights', sa.Float(), nullable=False),
    sa.Column('T1', sa.Float(), nullable=False),
    sa.Column('RH_1', sa.Float(), nullable=False),
    sa.Column('T2', sa.Float(), nullable=False),
    sa.Column('RH_2', sa.Float(), nullable=False),
    sa.Column('T3', sa.Float(), nullable=False),
    sa.Column('RH_3', sa.Float(), nullable=False),
    sa.Column('T4', sa.Float(), nullable=False),
    sa.Column('RH_4', sa.Float(), nullable=False),
    sa.Column('T5', sa.Float(), nullable=False),
    sa.Column('RH_5', sa.Float(), nullable=False),
    sa.Column('T6', sa.Float(), nullable=False),
    sa.Column('RH_6', sa.Float(), nullable=False),
    sa.Column('T7', sa.Float(), nullable=False),
    sa.Column('RH_7', sa.Float(), nullable=False),
    sa.Column('T8', sa.Float(), nullable=False),
    sa.Column('RH_8', sa.Float(), nullable=False),
    sa.Column('T9', sa.Float(), nullable=False),
    sa.Column('RH_9', sa.Float(), nullable=False),
    sa.Column('T_out', sa.Float(), nullable=False),
    sa.Column('Press_mm_hg', sa.Float(), nullable=False),
    sa.Column('RH_out', sa.Float(), nullable=False),
    sa.Column('Windspeed', sa.Float(), nullable=False),
    sa.Column('Visibility', sa.Float(), nullable=False),
    sa.Column('Tdewpoint', sa.Float(), nullable=False),
    sa.CheckConstraint('"Appliances" >= -1.7976931348623157e308 AND "Appliances" <= 1.7976931348623157e308', name=op.f('ck_measurements_appliances_finite')),
    sa.CheckConstraint('"Press_mm_hg" >= -1.7976931348623157e308 AND "Press_mm_hg" <= 1.7976931348623157e308', name=op.f('ck_measurements_press_mm_hg_finite')),
    sa.CheckConstraint('"RH_1" >= -1.7976931348623157e308 AND "RH_1" <= 1.7976931348623157e308', name=op.f('ck_measurements_rh_1_finite')),
    sa.CheckConstraint('"RH_2" >= -1.7976931348623157e308 AND "RH_2" <= 1.7976931348623157e308', name=op.f('ck_measurements_rh_2_finite')),
    sa.CheckConstraint('"RH_3" >= -1.7976931348623157e308 AND "RH_3" <= 1.7976931348623157e308', name=op.f('ck_measurements_rh_3_finite')),
    sa.CheckConstraint('"RH_4" >= -1.7976931348623157e308 AND "RH_4" <= 1.7976931348623157e308', name=op.f('ck_measurements_rh_4_finite')),
    sa.CheckConstraint('"RH_5" >= -1.7976931348623157e308 AND "RH_5" <= 1.7976931348623157e308', name=op.f('ck_measurements_rh_5_finite')),
    sa.CheckConstraint('"RH_6" >= -1.7976931348623157e308 AND "RH_6" <= 1.7976931348623157e308', name=op.f('ck_measurements_rh_6_finite')),
    sa.CheckConstraint('"RH_7" >= -1.7976931348623157e308 AND "RH_7" <= 1.7976931348623157e308', name=op.f('ck_measurements_rh_7_finite')),
    sa.CheckConstraint('"RH_8" >= -1.7976931348623157e308 AND "RH_8" <= 1.7976931348623157e308', name=op.f('ck_measurements_rh_8_finite')),
    sa.CheckConstraint('"RH_9" >= -1.7976931348623157e308 AND "RH_9" <= 1.7976931348623157e308', name=op.f('ck_measurements_rh_9_finite')),
    sa.CheckConstraint('"RH_out" >= -1.7976931348623157e308 AND "RH_out" <= 1.7976931348623157e308', name=op.f('ck_measurements_rh_out_finite')),
    sa.CheckConstraint('"T1" >= -1.7976931348623157e308 AND "T1" <= 1.7976931348623157e308', name=op.f('ck_measurements_t1_finite')),
    sa.CheckConstraint('"T2" >= -1.7976931348623157e308 AND "T2" <= 1.7976931348623157e308', name=op.f('ck_measurements_t2_finite')),
    sa.CheckConstraint('"T3" >= -1.7976931348623157e308 AND "T3" <= 1.7976931348623157e308', name=op.f('ck_measurements_t3_finite')),
    sa.CheckConstraint('"T4" >= -1.7976931348623157e308 AND "T4" <= 1.7976931348623157e308', name=op.f('ck_measurements_t4_finite')),
    sa.CheckConstraint('"T5" >= -1.7976931348623157e308 AND "T5" <= 1.7976931348623157e308', name=op.f('ck_measurements_t5_finite')),
    sa.CheckConstraint('"T6" >= -1.7976931348623157e308 AND "T6" <= 1.7976931348623157e308', name=op.f('ck_measurements_t6_finite')),
    sa.CheckConstraint('"T7" >= -1.7976931348623157e308 AND "T7" <= 1.7976931348623157e308', name=op.f('ck_measurements_t7_finite')),
    sa.CheckConstraint('"T8" >= -1.7976931348623157e308 AND "T8" <= 1.7976931348623157e308', name=op.f('ck_measurements_t8_finite')),
    sa.CheckConstraint('"T9" >= -1.7976931348623157e308 AND "T9" <= 1.7976931348623157e308', name=op.f('ck_measurements_t9_finite')),
    sa.CheckConstraint('"T_out" >= -1.7976931348623157e308 AND "T_out" <= 1.7976931348623157e308', name=op.f('ck_measurements_t_out_finite')),
    sa.CheckConstraint('"Tdewpoint" >= -1.7976931348623157e308 AND "Tdewpoint" <= 1.7976931348623157e308', name=op.f('ck_measurements_tdewpoint_finite')),
    sa.CheckConstraint('"Visibility" >= -1.7976931348623157e308 AND "Visibility" <= 1.7976931348623157e308', name=op.f('ck_measurements_visibility_finite')),
    sa.CheckConstraint('"Windspeed" >= -1.7976931348623157e308 AND "Windspeed" <= 1.7976931348623157e308', name=op.f('ck_measurements_windspeed_finite')),
    sa.CheckConstraint('"lights" >= -1.7976931348623157e308 AND "lights" <= 1.7976931348623157e308', name=op.f('ck_measurements_lights_finite')),
    sa.ForeignKeyConstraint(['building_id'], ['buildings.id'], name=op.f('fk_measurements_building_id_buildings'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_measurements')),
    sa.UniqueConstraint('building_id', 'timestamp', name='uq_measurements_building_timestamp')
    )
    op.create_index(op.f('ix_measurements_building_id'), 'measurements', ['building_id'], unique=False)
    op.create_index(op.f('ix_measurements_timestamp'), 'measurements', ['timestamp'], unique=False)
    op.create_table('predictions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('building_id', sa.Integer(), nullable=False),
    sa.Column('source_timestamp', sa.DateTime(), nullable=False),
    sa.Column('prediction_wh', sa.Float(), nullable=False),
    sa.Column('horizon_minutes', sa.Integer(), server_default='10', nullable=False),
    sa.Column('model_name', sa.String(length=200), nullable=False),
    sa.Column('model_checksum', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('recommendation_level', sa.String(length=20), nullable=True),
    sa.Column('recommendation_code', sa.String(length=100), nullable=True),
    sa.Column('recommendation_priority', sa.String(length=10), nullable=True),
    sa.Column('recommendation_text', sa.Text(), nullable=True),
    sa.CheckConstraint("recommendation_level IN ('NORMAL', 'ELEVATED', 'HIGH', 'VERY HIGH')", name=op.f('ck_predictions_valid_recommendation_level')),
    sa.CheckConstraint("recommendation_priority IN ('low', 'medium', 'high')", name=op.f('ck_predictions_valid_recommendation_priority')),
    sa.CheckConstraint('"prediction_wh" >= -1.7976931348623157e308 AND "prediction_wh" <= 1.7976931348623157e308', name=op.f('ck_predictions_prediction_wh_finite')),
    sa.CheckConstraint('(recommendation_level IS NULL AND recommendation_code IS NULL AND recommendation_priority IS NULL AND recommendation_text IS NULL) OR (recommendation_level IS NOT NULL AND recommendation_code IS NOT NULL AND recommendation_priority IS NOT NULL AND recommendation_text IS NOT NULL)', name=op.f('ck_predictions_complete_recommendation')),
    sa.CheckConstraint('horizon_minutes > 0', name=op.f('ck_predictions_positive_horizon')),
    sa.CheckConstraint('length(model_checksum) = 64', name=op.f('ck_predictions_checksum_length')),
    sa.ForeignKeyConstraint(['building_id'], ['buildings.id'], name=op.f('fk_predictions_building_id_buildings'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_predictions'))
    )
    op.create_index(op.f('ix_predictions_building_id'), 'predictions', ['building_id'], unique=False)
    op.create_index(op.f('ix_predictions_source_timestamp'), 'predictions', ['source_timestamp'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_predictions_source_timestamp'), table_name='predictions')
    op.drop_index(op.f('ix_predictions_building_id'), table_name='predictions')
    op.drop_table('predictions')
    op.drop_index(op.f('ix_measurements_timestamp'), table_name='measurements')
    op.drop_index(op.f('ix_measurements_building_id'), table_name='measurements')
    op.drop_table('measurements')
    op.drop_index(op.f('ix_buildings_owner_id'), table_name='buildings')
    op.drop_table('buildings')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
