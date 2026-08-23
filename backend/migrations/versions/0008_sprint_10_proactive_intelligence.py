"""sprint 10 proactive intelligence

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-22 18:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── proactive_event_record ───────────────────────────────────────────────
    op.create_table(
        'proactive_event_record',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False, server_default='internal'),
        sa.Column('fingerprint', sa.String(length=64), nullable=False),
        sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='RECEIVED'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_proactive_event_record_event_id'), 'proactive_event_record', ['event_id'], unique=True)
    op.create_index(op.f('ix_proactive_event_record_event_type'), 'proactive_event_record', ['event_type'], unique=False)
    op.create_index(op.f('ix_proactive_event_record_fingerprint'), 'proactive_event_record', ['fingerprint'], unique=False)
    op.create_index('ix_proactive_event_type_status', 'proactive_event_record', ['event_type', 'status'], unique=False)

    # ── proactive_decision_record ────────────────────────────────────────────
    op.create_table(
        'proactive_decision_record',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('decision_id', sa.UUID(), nullable=False),
        sa.Column('event_id', sa.UUID(), nullable=False),
        sa.Column('farmer_id', sa.Integer(), nullable=True),
        sa.Column('field_id', sa.Integer(), nullable=True),
        sa.Column('risk_type', sa.String(length=100), nullable=False),
        sa.Column('risk_severity', sa.String(length=50), nullable=False, server_default='LOW'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('evidence_package', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('workflow_version', sa.String(length=50), nullable=False, server_default='1.0.0'),
        sa.Column('agent_version', sa.String(length=50), nullable=False, server_default='1.0.0'),
        sa.Column('advisory_text', sa.Text(), nullable=False),
        sa.Column('requires_review', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['farmer_id'], ['farmer.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['field_id'], ['field.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_proactive_decision_record_decision_id'), 'proactive_decision_record', ['decision_id'], unique=True)
    op.create_index(op.f('ix_proactive_decision_record_event_id'), 'proactive_decision_record', ['event_id'], unique=False)
    op.create_index(op.f('ix_proactive_decision_record_farmer_id'), 'proactive_decision_record', ['farmer_id'], unique=False)
    op.create_index(op.f('ix_proactive_decision_record_field_id'), 'proactive_decision_record', ['field_id'], unique=False)
    op.create_index('ix_proactive_decision_farmer_created', 'proactive_decision_record', ['farmer_id', 'created_at'], unique=False)

    # ── alert_notification_record ────────────────────────────────────────────
    op.create_table(
        'alert_notification_record',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', sa.UUID(), nullable=False),
        sa.Column('decision_id', sa.Integer(), nullable=True),
        sa.Column('farmer_id', sa.Integer(), nullable=False),
        sa.Column('channel', sa.String(length=50), nullable=False, server_default='IN_APP'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(length=50), nullable=False, server_default='NORMAL'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='CREATED'),
        sa.Column('reviewed_by', sa.UUID(), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['decision_id'], ['proactive_decision_record.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['farmer_id'], ['farmer.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['user.uuid'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_notification_record_uuid'), 'alert_notification_record', ['uuid'], unique=True)
    op.create_index(op.f('ix_alert_notification_record_farmer_id'), 'alert_notification_record', ['farmer_id'], unique=False)
    op.create_index(op.f('ix_alert_notification_record_status'), 'alert_notification_record', ['status'], unique=False)
    op.create_index('ix_alert_notif_farmer_status', 'alert_notification_record', ['farmer_id', 'status'], unique=False)

    # ── notification_preference_record ───────────────────────────────────────
    op.create_table(
        'notification_preference_record',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('farmer_id', sa.Integer(), nullable=False),
        sa.Column('preferred_channel', sa.String(length=50), nullable=False, server_default='IN_APP'),
        sa.Column('preferred_language', sa.String(length=50), nullable=False, server_default='te'),
        sa.Column('min_severity', sa.String(length=50), nullable=False, server_default='LOW'),
        sa.Column('quiet_hours_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('quiet_hours_start', sa.String(length=10), nullable=False, server_default='22:00'),
        sa.Column('quiet_hours_end', sa.String(length=10), nullable=False, server_default='06:00'),
        sa.Column('enable_weather_alerts', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('enable_disease_alerts', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('enable_market_alerts', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('enable_scheme_alerts', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['farmer_id'], ['farmer.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('farmer_id')
    )
    op.create_index(op.f('ix_notification_preference_record_farmer_id'), 'notification_preference_record', ['farmer_id'], unique=True)


def downgrade() -> None:
    op.drop_table('notification_preference_record')
    op.drop_table('alert_notification_record')
    op.drop_table('proactive_decision_record')
    op.drop_table('proactive_event_record')
