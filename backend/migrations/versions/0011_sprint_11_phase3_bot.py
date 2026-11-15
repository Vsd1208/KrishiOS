"""sprint 11 phase 3: conversation turns, extension assignments, feedback, media

Additive only (new tables). The only link to an existing table is the extension assignment's
foreign key to ``farmer``.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-13 20:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def _ts() -> list[sa.Column]:
    return [sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False)]


def upgrade() -> None:
    op.create_table(
        "conversation_turn",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("turn_uuid", sa.String(32), nullable=False),
        sa.Column("conversation_id", sa.String(32), nullable=False),
        sa.Column("user_uuid", sa.UUID(), nullable=False),
        sa.Column("acting_for_farmer_id", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(16), nullable=False, server_default="text"),
        sa.Column("language", sa.String(8), nullable=False),
        sa.Column("detected_language", sa.String(8), nullable=True),
        sa.Column("user_text", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(32), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reply_text", sa.Text(), nullable=False),
        sa.Column("reply_text_en", sa.Text(), nullable=True),
        sa.Column("slots", sa.JSON(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("providers", sa.JSON(), nullable=False),
        sa.Column("translation_status", sa.String(20), nullable=True),
        sa.Column("requires_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("review_reason", sa.String(40), nullable=True),
        sa.Column("shared_with_farmer", sa.Boolean(), nullable=False,
                  server_default=sa.true()),
        *_ts(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("turn_uuid"),
    )
    op.create_index("ix_conversation_turn_conversation", "conversation_turn",
                    ["conversation_id"])
    op.create_index("ix_conversation_turn_review", "conversation_turn", ["requires_review"])

    op.create_table(
        "extension_assignment",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("worker_user_uuid", sa.UUID(), nullable=False),
        sa.Column("farmer_id", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("consent_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("consent_method", sa.String(32), nullable=True),
        sa.Column("consent_evidence", sa.Text(), nullable=True),
        sa.Column("consent_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_by", sa.UUID(), nullable=True),
        *_ts(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["farmer_id"], ["farmer.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("worker_user_uuid", "farmer_id", name="uq_extension_worker_farmer"),
    )
    op.create_index("ix_extension_assignment_worker", "extension_assignment",
                    ["worker_user_uuid", "active"])

    op.create_table(
        "answer_feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column("target_type", sa.String(16), nullable=False),
        sa.Column("target_id", sa.String(64), nullable=False),
        sa.Column("user_uuid", sa.UUID(), nullable=False),
        sa.Column("rating", sa.String(8), nullable=False),
        sa.Column("useful", sa.Boolean(), nullable=True),
        sa.Column("correct", sa.Boolean(), nullable=True),
        sa.Column("reason", sa.String(24), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("language", sa.String(8), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="new"),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index("ix_answer_feedback_target", "answer_feedback", ["target_type", "target_id"])
    op.create_index("ix_answer_feedback_status", "answer_feedback", ["status", "rating"])

    op.create_table(
        "media_asset",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("source_org", sa.String(150), nullable=False),
        sa.Column("licence", sa.String(150), nullable=True),
        sa.Column("licence_url", sa.String(1000), nullable=True),
        sa.Column("language", sa.String(8), nullable=False),
        sa.Column("crops", sa.JSON(), nullable=False),
        sa.Column("topics", sa.JSON(), nullable=False),
        sa.Column("duration_s", sa.Integer(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("added_by", sa.UUID(), nullable=True),
        sa.Column("verified_by", sa.UUID(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("knowledge_document_id", sa.Integer(), nullable=True),
        *_ts(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index("ix_media_asset_status", "media_asset", ["status"])


def downgrade() -> None:
    op.drop_index("ix_media_asset_status", table_name="media_asset")
    op.drop_table("media_asset")
    op.drop_index("ix_answer_feedback_status", table_name="answer_feedback")
    op.drop_index("ix_answer_feedback_target", table_name="answer_feedback")
    op.drop_table("answer_feedback")
    op.drop_index("ix_extension_assignment_worker", table_name="extension_assignment")
    op.drop_table("extension_assignment")
    op.drop_index("ix_conversation_turn_review", table_name="conversation_turn")
    op.drop_index("ix_conversation_turn_conversation", table_name="conversation_turn")
    op.drop_table("conversation_turn")
