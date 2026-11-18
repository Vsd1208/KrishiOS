"""sprint 11 phase 9: crowdsourced diagnosis reports (F8)

Additive only (one new table).

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-16 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diagnosis_report",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("lgd_district_code", sa.Integer(), nullable=False),
        sa.Column("crop_canonical", sa.String(length=64), nullable=False),
        sa.Column("condition", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("crop_confirmed_by_farmer", sa.Boolean(), nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=False),
        sa.Column("reporter_hash", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("week_start", "lgd_district_code", "crop_canonical", "condition",
                            "reporter_hash", name="uq_diagnosis_report_weekly"),
    )
    op.create_index("ix_diagnosis_report_week_district", "diagnosis_report",
                    ["week_start", "lgd_district_code"])


def downgrade() -> None:
    op.drop_table("diagnosis_report")
