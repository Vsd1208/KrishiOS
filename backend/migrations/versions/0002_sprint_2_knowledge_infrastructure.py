"""Create Sprint 2 knowledge infrastructure schema.

Tables created:
- knowledge_document
- document_chunk

Revision ID: 0002_sprint_2
Revises: 0001_sprint_1
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_sprint_2"
down_revision: str | None = "0001_sprint_1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Create document_status_enum type ─────────────────────────────────────
    document_status_enum = postgresql.ENUM(
        "pending",
        "parsing",
        "chunking",
        "embedding",
        "completed",
        "failed",
        name="document_status_enum",
        create_type=False,
    )
    document_status_enum.create(op.get_bind(), checkfirst=True)

    # ── knowledge_document ────────────────────────────────────────────────────
    op.create_table(
        "knowledge_document",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        # Content identity
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("document_type", sa.String(length=100), nullable=False),
        sa.Column("language", sa.String(length=50), nullable=False),
        # Provenance
        sa.Column("source", sa.String(length=300), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("authority", sa.String(length=300), nullable=True),
        # Agricultural context
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("district", sa.String(length=150), nullable=True),
        sa.Column("crop", sa.String(length=150), nullable=True),
        sa.Column("season", sa.String(length=50), nullable=True),
        # Upload metadata
        sa.Column("uploaded_by", sa.String(length=150), nullable=True),
        # File metadata
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        # Processing status
        sa.Column(
            "status",
            document_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
        sa.UniqueConstraint("file_hash"),
    )
    op.create_index("ix_knowledge_document_uuid", "knowledge_document", ["uuid"])
    op.create_index("ix_knowledge_document_file_hash", "knowledge_document", ["file_hash"])
    op.create_index("ix_knowledge_document_status", "knowledge_document", ["status"])
    op.create_index(
        "ix_kd_crop_district",
        "knowledge_document",
        ["crop", "district"],
    )
    op.create_index(
        "ix_kd_language_status",
        "knowledge_document",
        ["language", "status"],
    )

    # ── document_chunk ────────────────────────────────────────────────────────
    op.create_table(
        "document_chunk",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "chunk_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("document_id", sa.Integer(), nullable=False),
        # Position
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        # Content
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        # Embedding metadata
        sa.Column("embedding_model", sa.String(length=200), nullable=False),
        sa.Column("embedding_version", sa.String(length=50), nullable=False),
        # Agricultural payload
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        # Constraints
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["knowledge_document.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id"),
    )
    op.create_index("ix_document_chunk_chunk_id", "document_chunk", ["chunk_id"])
    op.create_index("ix_document_chunk_document_id", "document_chunk", ["document_id"])
    op.create_index(
        "ix_dc_document_index",
        "document_chunk",
        ["document_id", "chunk_index"],
    )
    op.create_index(
        "ix_dc_document_page",
        "document_chunk",
        ["document_id", "page_number"],
    )


def downgrade() -> None:
    # Drop document_chunk first (FK dependency)
    op.drop_index("ix_dc_document_page", table_name="document_chunk")
    op.drop_index("ix_dc_document_index", table_name="document_chunk")
    op.drop_index("ix_document_chunk_document_id", table_name="document_chunk")
    op.drop_index("ix_document_chunk_chunk_id", table_name="document_chunk")
    op.drop_table("document_chunk")

    # Drop knowledge_document
    op.drop_index("ix_kd_language_status", table_name="knowledge_document")
    op.drop_index("ix_kd_crop_district", table_name="knowledge_document")
    op.drop_index("ix_knowledge_document_status", table_name="knowledge_document")
    op.drop_index("ix_knowledge_document_file_hash", table_name="knowledge_document")
    op.drop_index("ix_knowledge_document_uuid", table_name="knowledge_document")
    op.drop_table("knowledge_document")

    # Drop enum type
    postgresql.ENUM(name="document_status_enum").drop(op.get_bind(), checkfirst=True)
