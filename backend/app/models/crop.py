"""Crop ORM model for the normalized KrishiOS crop catalog."""

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.field_crop import FieldCrop


class Crop(TimestampMixin, SoftDeleteMixin, Base):
    """Cultivated crop metadata used by field crop history records."""

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crop_name: Mapped[str] = mapped_column(String(150), nullable=False)
    scientific_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    season: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_days: Mapped[int] = mapped_column(nullable=False)

    field_history: Mapped[list["FieldCrop"]] = relationship(back_populates="crop")

    __table_args__ = (
        UniqueConstraint("crop_name", "season", name="uq_crop_name_season"),
        CheckConstraint("duration_days > 0", name="ck_crop_duration_positive"),
        Index("ix_crop_name", "crop_name"),
        Index("ix_crop_season", "season"),
    )
