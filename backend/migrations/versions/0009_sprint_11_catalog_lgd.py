"""sprint 11 crop catalog and LGD codes

Additive only: new ``crop_catalog`` table and nullable columns on ``district`` and ``crop``.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-12 19:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crop_catalog",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("crop_canonical", sa.String(length=64), nullable=False),
        sa.Column("name_en", sa.String(length=150), nullable=False),
        sa.Column("name_te", sa.String(length=150), nullable=False),
        sa.Column("name_hi", sa.String(length=150), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("scientific_name", sa.String(length=150), nullable=True),
        sa.Column("crop_group", sa.String(length=50), nullable=False),
        sa.Column("domain", sa.String(length=20), nullable=False, server_default="crop"),
        sa.Column("seasons", sa.JSON(), nullable=False),
        sa.Column("yield_unit", sa.String(length=30), nullable=False),
        sa.Column("apy_names", sa.JSON(), nullable=False),
        sa.Column("tier", sa.String(length=20), nullable=False, server_default="unassigned"),
        sa.Column("vision_supported", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("crop_canonical"),
    )
    op.create_index("ix_crop_catalog_group", "crop_catalog", ["crop_group"])

    op.add_column("district", sa.Column("lgd_district_code", sa.Integer(), nullable=True))
    op.add_column("district", sa.Column("lgd_state_code", sa.Integer(), nullable=True))
    op.add_column("district", sa.Column("census_2011_code", sa.Integer(), nullable=True))
    op.create_unique_constraint("uq_district_lgd_code", "district", ["lgd_district_code"])

    op.add_column("crop", sa.Column("catalog_canonical", sa.String(length=64), nullable=True))
    op.create_index("ix_crop_catalog_canonical", "crop", ["catalog_canonical"])


def downgrade() -> None:
    op.drop_index("ix_crop_catalog_canonical", table_name="crop")
    op.drop_column("crop", "catalog_canonical")
    op.drop_constraint("uq_district_lgd_code", "district", type_="unique")
    op.drop_column("district", "census_2011_code")
    op.drop_column("district", "lgd_state_code")
    op.drop_column("district", "lgd_district_code")
    op.drop_index("ix_crop_catalog_group", table_name="crop_catalog")
    op.drop_table("crop_catalog")
