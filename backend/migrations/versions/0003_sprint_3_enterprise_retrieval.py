"""Create Sprint 3 enterprise retrieval index state.

Revision ID: 0003_sprint_3
Revises: 0002_sprint_2
Create Date: 2026-07-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_sprint_3"
down_revision: str | None = "0002_sprint_2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    index_kind = postgresql.ENUM(
        "GOVERNMENT_DOCUMENTS",
        "RESEARCH_PAPERS",
        "OFFICER_REPORTS",
        "WEATHER_ADVISORIES",
        "KNOWLEDGE_GRAPH",
        "BASE",
        "DELTA",
        name="retrieval_index_kind",
        create_type=False,
    )
    index_status = postgresql.ENUM(
        "BUILDING",
        "VALIDATING",
        "READY",
        "ACTIVE",
        "FAILED",
        "ROLLED_BACK",
        "DELETED",
        name="retrieval_index_status",
        create_type=False,
    )
    build_mode = postgresql.ENUM(
        "FULL",
        "INCREMENTAL",
        "DELTA",
        "BLUE_GREEN",
        name="retrieval_build_mode",
        create_type=False,
    )
    index_kind.create(op.get_bind(), checkfirst=True)
    index_status.create(op.get_bind(), checkfirst=True)
    build_mode.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "retrieval_index_version",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("collection_name", sa.String(length=200), nullable=False),
        sa.Column("alias_name", sa.String(length=200), nullable=False),
        sa.Column("index_kind", index_kind, nullable=False),
        sa.Column("status", index_status, nullable=False),
        sa.Column("build_mode", build_mode, nullable=False),
        sa.Column("embedding_model", sa.String(length=200), nullable=False),
        sa.Column("embedding_version", sa.String(length=50), nullable=False),
        sa.Column("vector_size", sa.Integer(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("document_count", sa.Integer(), nullable=False),
        sa.Column("validation_report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alias_name", "version_number", name="uq_retrieval_alias_version"),
        sa.UniqueConstraint("collection_name"),
    )
    op.create_index(
        "ix_retrieval_index_version_alias_name",
        "retrieval_index_version",
        ["alias_name"],
    )
    op.create_index(
        "ix_retrieval_index_version_status",
        "retrieval_index_version",
        ["status"],
    )
    op.create_index(
        "ix_retrieval_index_kind_status",
        "retrieval_index_version",
        ["index_kind", "status"],
    )

    op.create_table(
        "indexed_document_state",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("index_version_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("document_hash", sa.String(length=64), nullable=False),
        sa.Column("content_checksum", sa.String(length=64), nullable=False),
        sa.Column("embedding_version", sa.String(length=50), nullable=False),
        sa.Column("last_modified", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_indexed", sa.DateTime(timezone=True), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["knowledge_document.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["index_version_id"],
            ["retrieval_index_version.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("index_version_id", "document_id", name="uq_indexed_document_state"),
    )
    op.create_index(
        "ix_indexed_document_state_document_id",
        "indexed_document_state",
        ["document_id"],
    )
    op.create_index(
        "ix_indexed_document_state_index_version_id",
        "indexed_document_state",
        ["index_version_id"],
    )
    op.create_index(
        "ix_indexed_document_hash_version",
        "indexed_document_state",
        ["document_hash", "embedding_version"],
    )


def downgrade() -> None:
    op.drop_index("ix_indexed_document_hash_version", table_name="indexed_document_state")
    op.drop_index("ix_indexed_document_state_index_version_id", table_name="indexed_document_state")
    op.drop_index("ix_indexed_document_state_document_id", table_name="indexed_document_state")
    op.drop_table("indexed_document_state")

    op.drop_index("ix_retrieval_index_kind_status", table_name="retrieval_index_version")
    op.drop_index("ix_retrieval_index_version_status", table_name="retrieval_index_version")
    op.drop_index("ix_retrieval_index_version_alias_name", table_name="retrieval_index_version")
    op.drop_table("retrieval_index_version")

    postgresql.ENUM(name="retrieval_build_mode").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="retrieval_index_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="retrieval_index_kind").drop(op.get_bind(), checkfirst=True)
