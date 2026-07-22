"""Soil sample ORM model for field-level sample collection workflows."""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.farmer import Farmer
    from app.models.field import Field
    from app.models.officer import Officer


class SoilSampleStatus(StrEnum):
    """Lifecycle states for a collected soil sample."""

    COLLECTED = "Collected"
    IN_TRANSIT = "In Transit"
    TESTING = "Testing"
    COMPLETED = "Completed"
    DELIVERED = "Delivered"


class SoilSample(TimestampMixin, SoftDeleteMixin, Base):
    """Physical soil sample collected from a farmer field by an officer."""

    __tablename__ = "soil_sample"

    sample_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sample_uuid: Mapped[UUID] = mapped_column(
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
    field_id: Mapped[int] = mapped_column(
        ForeignKey("field.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    collector_id: Mapped[int] = mapped_column(
        ForeignKey("officer.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    collection_date: Mapped[date] = mapped_column(Date, nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    status: Mapped[SoilSampleStatus] = mapped_column(
        Enum(SoilSampleStatus, name="soil_sample_status"),
        nullable=False,
        default=SoilSampleStatus.COLLECTED,
    )

    farmer: Mapped["Farmer"] = relationship(back_populates="soil_samples")
    field: Mapped["Field"] = relationship(back_populates="soil_samples")
    collector: Mapped["Officer"] = relationship(back_populates="collected_soil_samples")

    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_soil_sample_latitude_range"),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="ck_soil_sample_longitude_range",
        ),
        Index("ix_soil_sample_field_status", "field_id", "status"),
        Index("ix_soil_sample_collector_date", "collector_id", "collection_date"),
        Index("ix_soil_sample_farmer_date", "farmer_id", "collection_date"),
    )
