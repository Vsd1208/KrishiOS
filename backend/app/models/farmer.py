"""Farmer ORM model representing a primary KrishiOS domain actor."""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.district import District
    from app.models.field import Field
    from app.models.soil_sample import SoilSample


class Farmer(TimestampMixin, SoftDeleteMixin, Base):
    """Farmer profile with landholding and geographic ownership context."""

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    farmer_code: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        default=uuid4,
        unique=True,
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(15), nullable=False, unique=True, index=True)
    preferred_language: Mapped[str] = mapped_column(String(50), nullable=False)
    district_id: Mapped[int] = mapped_column(
        ForeignKey("district.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    village: Mapped[str] = mapped_column(String(150), nullable=False)
    landholding_acres: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    district: Mapped["District"] = relationship(back_populates="farmers")
    fields: Mapped[list["Field"]] = relationship(back_populates="farmer")
    soil_samples: Mapped[list["SoilSample"]] = relationship(back_populates="farmer")

    __table_args__ = (
        CheckConstraint("landholding_acres >= 0", name="ck_farmer_landholding_non_negative"),
        CheckConstraint("char_length(phone) >= 10", name="ck_farmer_phone_min_length"),
        Index("ix_farmer_district_village", "district_id", "village"),
    )
