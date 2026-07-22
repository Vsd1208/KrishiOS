"""Field crop history ORM model linking fields to crop lifecycles."""

from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.crop import Crop
    from app.models.field import Field


class FieldCropStatus(StrEnum):
    """Lifecycle states for a crop grown on a field."""

    PLANNED = "Planned"
    SOWN = "Sown"
    GROWING = "Growing"
    HARVESTED = "Harvested"
    FAILED = "Failed"


class FieldCrop(TimestampMixin, SoftDeleteMixin, Base):
    """Historical record of a crop cultivated on a field."""

    __tablename__ = "field_crop"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    field_id: Mapped[int] = mapped_column(
        ForeignKey("field.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    crop_id: Mapped[int] = mapped_column(
        ForeignKey("crop.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sowing_date: Mapped[date] = mapped_column(Date, nullable=False)
    harvesting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[FieldCropStatus] = mapped_column(
        Enum(FieldCropStatus, name="field_crop_status"),
        nullable=False,
        default=FieldCropStatus.PLANNED,
    )

    field: Mapped["Field"] = relationship(back_populates="crop_history")
    crop: Mapped["Crop"] = relationship(back_populates="field_history")

    __table_args__ = (
        UniqueConstraint("field_id", "crop_id", "sowing_date", name="uq_field_crop_sowing"),
        CheckConstraint(
            "harvesting_date IS NULL OR harvesting_date >= sowing_date",
            name="ck_field_crop_harvest_after_sowing",
        ),
        Index("ix_field_crop_field_status", "field_id", "status"),
    )
