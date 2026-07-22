"""Officer ORM model for district-scoped agricultural operations staff."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.district import District
    from app.models.soil_sample import SoilSample


class Officer(TimestampMixin, SoftDeleteMixin, Base):
    """Officer profile for field collection, extension, and district coordination."""

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    officer_code: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        default=uuid4,
        unique=True,
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(15), nullable=False, unique=True, index=True)
    designation: Mapped[str] = mapped_column(String(100), nullable=False)
    district_id: Mapped[int] = mapped_column(
        ForeignKey("district.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    district: Mapped["District"] = relationship(back_populates="officers")
    collected_soil_samples: Mapped[list["SoilSample"]] = relationship(back_populates="collector")

    __table_args__ = (
        CheckConstraint("char_length(phone) >= 10", name="ck_officer_phone_min_length"),
        Index("ix_officer_district_designation", "district_id", "designation"),
    )
