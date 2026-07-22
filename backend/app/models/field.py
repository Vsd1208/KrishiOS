"""Field ORM model representing an agricultural plot owned by a farmer."""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Index, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.farmer import Farmer
    from app.models.field_crop import FieldCrop
    from app.models.soil_sample import SoilSample


class Field(TimestampMixin, SoftDeleteMixin, Base):
    """A farmer-owned plot with location, size, soil, and irrigation metadata."""

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    field_code: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        default=uuid4,
        unique=True,
        nullable=False,
        index=True,
    )
    farmer_id: Mapped[int] = mapped_column(
        ForeignKey("farmer.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    field_name: Mapped[str] = mapped_column(String(150), nullable=False)
    area: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    soil_type: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    polygon_geojson: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    irrigation_type: Mapped[str] = mapped_column(String(100), nullable=False)

    farmer: Mapped["Farmer"] = relationship(back_populates="fields")
    crop_history: Mapped[list["FieldCrop"]] = relationship(back_populates="field")
    soil_samples: Mapped[list["SoilSample"]] = relationship(back_populates="field")

    __table_args__ = (
        UniqueConstraint("farmer_id", "field_name", name="uq_field_farmer_name"),
        CheckConstraint("area > 0", name="ck_field_area_positive"),
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_field_latitude_range"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_field_longitude_range"),
        Index("ix_field_farmer_soil_type", "farmer_id", "soil_type"),
    )
