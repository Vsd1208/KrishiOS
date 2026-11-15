"""sprint 11 phase 5: district weather feed snapshots

Additive only (one new table).

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-14 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "district_weather_snapshot",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lgd_district_code", sa.Integer(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("forecast", sa.JSON(), nullable=False),
        sa.Column("crosscheck", sa.JSON(), nullable=False),
        sa.Column("spray", sa.JSON(), nullable=False),
        sa.Column("providers", sa.JSON(), nullable=False),
        sa.Column("events_emitted", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_district_weather_snapshot_lgd_district_code",
                    "district_weather_snapshot", ["lgd_district_code"])
    op.create_index("ix_district_weather_snapshot_fetched_at", "district_weather_snapshot",
                    ["fetched_at"])


def downgrade() -> None:
    op.drop_table("district_weather_snapshot")
