"""sprint 11 phase 4: govt connect bulletins, delivery, audit, farmer locations, grievances, schemes

Additive only: new tables plus a nullable ``conversation_turn.bulletin_uuid`` column.
Pre-existing model/DB drift detected by autogenerate was deliberately left out.

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-14 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

_TABLES = (
    "grievance_event",
    "grievance_ticket",
    "govt_bulletin_delivery",
    "farmer_location",
    "govt_bulletin_translation",
    "govconnect_audit",
    "scheme_entry",
    "govt_bulletin",
)


def upgrade() -> None:
    op.create_table(
        "govt_bulletin",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_name", sa.String(length=200), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("file_sha256", sa.String(length=64), nullable=True),
        sa.Column("authority", sa.String(length=200), nullable=False),
        sa.Column("authority_level", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("original_language", sa.String(length=8), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hazard_type", sa.String(length=32), nullable=True),
        sa.Column("severity", sa.String(length=10), nullable=False),
        sa.Column("district_codes", sa.JSON(), nullable=False),
        sa.Column("block_codes", sa.JSON(), nullable=False),
        sa.Column("crops", sa.JSON(), nullable=False),
        sa.Column("recommended_actions", sa.JSON(), nullable=False),
        sa.Column("target_languages", sa.JSON(), nullable=False),
        sa.Column("segment", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("extraction", sa.JSON(), nullable=False),
        sa.Column("supersedes_id", sa.Integer(), nullable=True),
        sa.Column("knowledge_document_id", sa.Integer(), nullable=True),
        sa.Column("index_state", sa.String(length=10), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["supersedes_id"], ["govt_bulletin.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(op.f("ix_govt_bulletin_status"), "govt_bulletin", ["status"], unique=False)
    op.create_index(op.f("ix_govt_bulletin_valid_to"), "govt_bulletin", ["valid_to"], unique=False)
    op.create_table(
        "scheme_entry",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("names", sa.JSON(), nullable=False),
        sa.Column("authority", sa.String(length=200), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("state_codes", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("benefits", sa.JSON(), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("status_lookup_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("verified_by", sa.Uuid(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_table(
        "govconnect_audit",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bulletin_id", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bulletin_id"], ["govt_bulletin.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_govconnect_audit_bulletin_id"), "govconnect_audit", ["bulletin_id"], unique=False
    )
    op.create_table(
        "govt_bulletin_translation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bulletin_id", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("check_issues", sa.JSON(), nullable=False),
        sa.Column("back_translation", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bulletin_id"], ["govt_bulletin.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bulletin_id", "language", name="uq_bulletin_language"),
    )
    op.create_table(
        "farmer_location",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("farmer_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("lgd_district_code", sa.Integer(), nullable=False),
        sa.Column("lgd_block_code", sa.Integer(), nullable=True),
        sa.Column("village", sa.String(length=150), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["farmer_id"], ["farmer.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_farmer_location_farmer_id"), "farmer_location", ["farmer_id"], unique=False
    )
    op.create_table(
        "govt_bulletin_delivery",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bulletin_id", sa.Integer(), nullable=False),
        sa.Column("farmer_id", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("match_level", sa.String(length=10), nullable=False),
        sa.Column("notification_status", sa.String(length=16), nullable=False),
        sa.Column("alert_uuid", sa.Uuid(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("flag_reason", sa.String(length=32), nullable=True),
        sa.Column("flag_comment", sa.Text(), nullable=True),
        sa.Column("flagged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("flag_status", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bulletin_id"], ["govt_bulletin.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["farmer_id"], ["farmer.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bulletin_id", "farmer_id", name="uq_delivery_bulletin_farmer"),
    )
    op.create_index("ix_delivery_farmer", "govt_bulletin_delivery", ["farmer_id"], unique=False)
    op.create_table(
        "grievance_ticket",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.Uuid(), nullable=False),
        sa.Column("farmer_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("lgd_district_code", sa.Integer(), nullable=True),
        sa.Column("scheme_key", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("priority", sa.String(length=8), nullable=False),
        sa.Column("assigned_to", sa.Uuid(), nullable=True),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["farmer_id"], ["farmer.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        op.f("ix_grievance_ticket_farmer_id"), "grievance_ticket", ["farmer_id"], unique=False
    )
    op.create_index(
        op.f("ix_grievance_ticket_lgd_district_code"),
        "grievance_ticket",
        ["lgd_district_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_grievance_ticket_status"), "grievance_ticket", ["status"], unique=False
    )
    op.create_table(
        "grievance_event",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("public", sa.Boolean(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["grievance_ticket.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_grievance_event_ticket_id"), "grievance_event", ["ticket_id"], unique=False
    )
    op.add_column(
        "conversation_turn", sa.Column("bulletin_uuid", sa.String(length=36), nullable=True)
    )
    op.create_index(
        op.f("ix_conversation_turn_bulletin_uuid"),
        "conversation_turn",
        ["bulletin_uuid"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_turn_bulletin_uuid", table_name="conversation_turn")
    op.drop_column("conversation_turn", "bulletin_uuid")
    for table in _TABLES:
        op.drop_table(table)  # indexes and constraints go with the table
