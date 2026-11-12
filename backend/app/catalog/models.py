"""ORM mirror of the crop catalog (seeded from ``ml/reference/crop_catalog.csv``)."""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.base import TimestampMixin


class CropCatalogEntry(TimestampMixin, Base):
    """Canonical crop with multilingual names; FK target for forecasts and bulletins."""

    __tablename__ = "crop_catalog"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crop_canonical: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(150), nullable=False)
    name_te: Mapped[str] = mapped_column(String(150), nullable=False)
    name_hi: Mapped[str] = mapped_column(String(150), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    scientific_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    crop_group: Mapped[str] = mapped_column(String(50), nullable=False)
    domain: Mapped[str] = mapped_column(String(20), nullable=False, default="crop")
    seasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    yield_unit: Mapped[str] = mapped_column(String(30), nullable=False)
    apy_names: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="unassigned")
    vision_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    __table_args__ = (Index("ix_crop_catalog_group", "crop_group"),)
