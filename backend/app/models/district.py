"""District ORM model for normalized geographic references."""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.farmer import Farmer
    from app.models.officer import Officer


class District(TimestampMixin, SoftDeleteMixin, Base):
    """Administrative district used to group farmers, officers, and fields."""

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    district_name: Mapped[str] = mapped_column(String(150), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)

    farmers: Mapped[list["Farmer"]] = relationship(back_populates="district")
    officers: Mapped[list["Officer"]] = relationship(back_populates="district")

    __table_args__ = (
        UniqueConstraint("state", "district_name", name="uq_district_state_name"),
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_district_latitude_range"),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="ck_district_longitude_range",
        ),
        Index("ix_district_state_name", "state", "district_name"),
    )
