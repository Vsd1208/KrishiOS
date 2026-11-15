"""sprint 11 phase 8: imported yield forecasts

Additive only (two new tables).

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-15 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "yield_forecast_import",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_name", sa.String(length=80), nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("rows", sa.Integer(), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_version", "file_sha256", name="uq_forecast_import_file"),
    )
    op.create_table(
        "yield_forecast",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("import_id", sa.Integer(), nullable=False),
        sa.Column("lgd_district_code", sa.Integer(), nullable=False),
        sa.Column("crop_canonical", sa.String(length=64), nullable=False),
        sa.Column("season", sa.String(length=20), nullable=False),
        sa.Column("crop_year", sa.Integer(), nullable=False),
        sa.Column("crop_tier", sa.String(length=4), nullable=False),
        sa.Column("forecast_lead", sa.Integer(), nullable=False),
        sa.Column("predicted_yield", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("interval_low", sa.Float(), nullable=True),
        sa.Column("interval_high", sa.Float(), nullable=True),
        sa.Column("normal_yield", sa.Float(), nullable=True),
        sa.Column("available_modalities", sa.JSON(), nullable=False),
        sa.Column("missing_modalities", sa.JSON(), nullable=False),
        sa.Column("in_distribution", sa.Boolean(), nullable=False),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False),
        sa.Column("abstained", sa.Boolean(), nullable=False),
        sa.Column("abstain_reason", sa.String(length=200), nullable=True),
        sa.Column("model_name", sa.String(length=80), nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_version", "lgd_district_code", "crop_canonical", "season",
                            "crop_year", "forecast_lead", name="uq_yield_forecast_row"),
    )
    op.create_index("ix_yield_forecast_import_id", "yield_forecast", ["import_id"])
    op.create_index("ix_yield_forecast_lookup", "yield_forecast",
                    ["lgd_district_code", "crop_canonical", "season", "crop_year"])


def downgrade() -> None:
    op.drop_table("yield_forecast")
    op.drop_table("yield_forecast_import")
