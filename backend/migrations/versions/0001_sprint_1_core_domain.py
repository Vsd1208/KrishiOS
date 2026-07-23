"""Create Sprint 1 core agricultural domain schema.

Revision ID: 0001_sprint_1
Revises: None
Create Date: 2026-07-22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_sprint_1"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    field_crop_status = postgresql.ENUM(
        "PLANNED",
        "SOWN",
        "GROWING",
        "HARVESTED",
        "FAILED",
        name="field_crop_status",
        create_type=False,
    )
    soil_sample_status = postgresql.ENUM(
        "COLLECTED",
        "IN_TRANSIT",
        "TESTING",
        "COMPLETED",
        "DELIVERED",
        name="soil_sample_status",
        create_type=False,
    )
    field_crop_status.create(op.get_bind(), checkfirst=True)
    soil_sample_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "district",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("district_name", sa.String(length=150), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_district_latitude_range"),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="ck_district_longitude_range",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state", "district_name", name="uq_district_state_name"),
    )
    op.create_index("ix_district_state_name", "district", ["state", "district_name"])

    op.create_table(
        "crop",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("crop_name", sa.String(length=150), nullable=False),
        sa.Column("scientific_name", sa.String(length=150), nullable=True),
        sa.Column("season", sa.String(length=50), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("duration_days > 0", name="ck_crop_duration_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("crop_name", "season", name="uq_crop_name_season"),
    )
    op.create_index("ix_crop_name", "crop", ["crop_name"])
    op.create_index("ix_crop_season", "crop", ["season"])

    op.create_table(
        "farmer",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("farmer_code", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=15), nullable=False),
        sa.Column("preferred_language", sa.String(length=50), nullable=False),
        sa.Column("district_id", sa.Integer(), nullable=False),
        sa.Column("village", sa.String(length=150), nullable=False),
        sa.Column("landholding_acres", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("char_length(phone) >= 10", name="ck_farmer_phone_min_length"),
        sa.CheckConstraint("landholding_acres >= 0", name="ck_farmer_landholding_non_negative"),
        sa.ForeignKeyConstraint(["district_id"], ["district.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("farmer_code"),
        sa.UniqueConstraint("phone"),
    )
    op.create_index("ix_farmer_district_id", "farmer", ["district_id"])
    op.create_index("ix_farmer_district_village", "farmer", ["district_id", "village"])
    op.create_index("ix_farmer_farmer_code", "farmer", ["farmer_code"])
    op.create_index("ix_farmer_phone", "farmer", ["phone"])

    op.create_table(
        "officer",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("officer_code", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=15), nullable=False),
        sa.Column("designation", sa.String(length=100), nullable=False),
        sa.Column("district_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("char_length(phone) >= 10", name="ck_officer_phone_min_length"),
        sa.ForeignKeyConstraint(["district_id"], ["district.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("officer_code"),
        sa.UniqueConstraint("phone"),
    )
    op.create_index("ix_officer_district_designation", "officer", ["district_id", "designation"])
    op.create_index("ix_officer_district_id", "officer", ["district_id"])
    op.create_index("ix_officer_email", "officer", ["email"])
    op.create_index("ix_officer_officer_code", "officer", ["officer_code"])
    op.create_index("ix_officer_phone", "officer", ["phone"])

    op.create_table(
        "field",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("field_code", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("farmer_id", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(length=150), nullable=False),
        sa.Column("area", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("soil_type", sa.String(length=100), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("polygon_geojson", sa.JSON(), nullable=True),
        sa.Column("irrigation_type", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("area > 0", name="ck_field_area_positive"),
        sa.CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_field_latitude_range"),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="ck_field_longitude_range",
        ),
        sa.ForeignKeyConstraint(["farmer_id"], ["farmer.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("farmer_id", "field_name", name="uq_field_farmer_name"),
        sa.UniqueConstraint("field_code"),
    )
    op.create_index("ix_field_farmer_id", "field", ["farmer_id"])
    op.create_index("ix_field_farmer_soil_type", "field", ["farmer_id", "soil_type"])
    op.create_index("ix_field_field_code", "field", ["field_code"])

    op.create_table(
        "field_crop",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("field_id", sa.Integer(), nullable=False),
        sa.Column("crop_id", sa.Integer(), nullable=False),
        sa.Column("sowing_date", sa.Date(), nullable=False),
        sa.Column("harvesting_date", sa.Date(), nullable=True),
        sa.Column("status", field_crop_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "harvesting_date IS NULL OR harvesting_date >= sowing_date",
            name="ck_field_crop_harvest_after_sowing",
        ),
        sa.ForeignKeyConstraint(["crop_id"], ["crop.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["field_id"], ["field.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("field_id", "crop_id", "sowing_date", name="uq_field_crop_sowing"),
    )
    op.create_index("ix_field_crop_crop_id", "field_crop", ["crop_id"])
    op.create_index("ix_field_crop_field_id", "field_crop", ["field_id"])
    op.create_index("ix_field_crop_field_status", "field_crop", ["field_id", "status"])

    op.create_table(
        "soil_sample",
        sa.Column("sample_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sample_uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("farmer_id", sa.Integer(), nullable=False),
        sa.Column("field_id", sa.Integer(), nullable=False),
        sa.Column("collector_id", sa.Integer(), nullable=False),
        sa.Column("collection_date", sa.Date(), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("status", soil_sample_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name="ck_soil_sample_latitude_range",
        ),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="ck_soil_sample_longitude_range",
        ),
        sa.ForeignKeyConstraint(["collector_id"], ["officer.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["farmer_id"], ["farmer.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["field_id"], ["field.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("sample_id"),
        sa.UniqueConstraint("sample_uuid"),
    )
    op.create_index(
        "ix_soil_sample_collector_date",
        "soil_sample",
        ["collector_id", "collection_date"],
    )
    op.create_index("ix_soil_sample_collector_id", "soil_sample", ["collector_id"])
    op.create_index("ix_soil_sample_farmer_date", "soil_sample", ["farmer_id", "collection_date"])
    op.create_index("ix_soil_sample_farmer_id", "soil_sample", ["farmer_id"])
    op.create_index("ix_soil_sample_field_id", "soil_sample", ["field_id"])
    op.create_index("ix_soil_sample_field_status", "soil_sample", ["field_id", "status"])
    op.create_index("ix_soil_sample_sample_uuid", "soil_sample", ["sample_uuid"])


def downgrade() -> None:
    op.drop_index("ix_soil_sample_sample_uuid", table_name="soil_sample")
    op.drop_index("ix_soil_sample_field_status", table_name="soil_sample")
    op.drop_index("ix_soil_sample_field_id", table_name="soil_sample")
    op.drop_index("ix_soil_sample_farmer_id", table_name="soil_sample")
    op.drop_index("ix_soil_sample_farmer_date", table_name="soil_sample")
    op.drop_index("ix_soil_sample_collector_id", table_name="soil_sample")
    op.drop_index("ix_soil_sample_collector_date", table_name="soil_sample")
    op.drop_table("soil_sample")

    op.drop_index("ix_field_crop_field_status", table_name="field_crop")
    op.drop_index("ix_field_crop_field_id", table_name="field_crop")
    op.drop_index("ix_field_crop_crop_id", table_name="field_crop")
    op.drop_table("field_crop")

    op.drop_index("ix_field_field_code", table_name="field")
    op.drop_index("ix_field_farmer_soil_type", table_name="field")
    op.drop_index("ix_field_farmer_id", table_name="field")
    op.drop_table("field")

    op.drop_index("ix_officer_phone", table_name="officer")
    op.drop_index("ix_officer_officer_code", table_name="officer")
    op.drop_index("ix_officer_email", table_name="officer")
    op.drop_index("ix_officer_district_id", table_name="officer")
    op.drop_index("ix_officer_district_designation", table_name="officer")
    op.drop_table("officer")

    op.drop_index("ix_farmer_phone", table_name="farmer")
    op.drop_index("ix_farmer_farmer_code", table_name="farmer")
    op.drop_index("ix_farmer_district_village", table_name="farmer")
    op.drop_index("ix_farmer_district_id", table_name="farmer")
    op.drop_table("farmer")

    op.drop_index("ix_crop_season", table_name="crop")
    op.drop_index("ix_crop_name", table_name="crop")
    op.drop_table("crop")

    op.drop_index("ix_district_state_name", table_name="district")
    op.drop_table("district")

    postgresql.ENUM(name="soil_sample_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="field_crop_status").drop(op.get_bind(), checkfirst=True)
