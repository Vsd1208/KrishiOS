"""sprint 11 translation records

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-12 21:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "translation_record",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("source_language", sa.String(length=8), nullable=False),
        sa.Column("target_language", sa.String(length=8), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=False),
        sa.Column("back_translation", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("provider_version", sa.String(length=64), nullable=True),
        sa.Column("glossary_version", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("attempts", sa.JSON(), nullable=False),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("edited_by_reviewer", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index("ix_translation_record_hash", "translation_record", ["content_hash"])
    op.create_index("ix_translation_record_status", "translation_record", ["status"])


def downgrade() -> None:
    op.drop_index("ix_translation_record_status", table_name="translation_record")
    op.drop_index("ix_translation_record_hash", table_name="translation_record")
    op.drop_table("translation_record")
