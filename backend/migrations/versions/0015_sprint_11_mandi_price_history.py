"""sprint 11: official AGMARKNET daily price history

Additive only (one new table).

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-14 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mandi_price_daily",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("arrival_date", sa.Date(), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=False),
        sa.Column("market", sa.String(length=150), nullable=False),
        sa.Column("commodity", sa.String(length=150), nullable=False),
        sa.Column("variety", sa.String(length=150), nullable=False),
        sa.Column("grade", sa.String(length=60), nullable=False),
        sa.Column("crop_canonical", sa.String(length=64), nullable=True),
        sa.Column("min_price", sa.Float(), nullable=True),
        sa.Column("max_price", sa.Float(), nullable=True),
        sa.Column("modal_price", sa.Float(), nullable=False),
        sa.Column("source_resource", sa.String(length=64), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("arrival_date", "state", "district", "market", "commodity",
                            "variety", "grade", name="uq_mandi_price_row"),
    )
    op.create_index("ix_mandi_price_daily_arrival_date", "mandi_price_daily", ["arrival_date"])
    op.create_index("ix_mandi_price_daily_district", "mandi_price_daily", ["district"])
    op.create_index("ix_mandi_price_daily_crop_canonical", "mandi_price_daily",
                    ["crop_canonical"])
    op.create_index("ix_mandi_crop_district_date", "mandi_price_daily",
                    ["crop_canonical", "district", "arrival_date"])


def downgrade() -> None:
    op.drop_table("mandi_price_daily")
