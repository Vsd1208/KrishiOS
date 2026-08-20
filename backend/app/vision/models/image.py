"""CropImage model storing metadata for uploaded farm images."""

from uuid import UUID, uuid4
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin


class CropImage(TimestampMixin, Base):
    """Metadata for an uploaded crop image. Binary data is stored externally."""

    __tablename__ = "crop_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        default=uuid4,
        unique=True,
        nullable=False,
        index=True,
    )
    
    owner_uuid: Mapped[UUID] = mapped_column(
        ForeignKey("user.uuid", ondelete="CASCADE"), nullable=False, index=True
    )
    field_id: Mapped[int | None] = mapped_column(
        ForeignKey("field.id", ondelete="SET NULL"), nullable=True, index=True
    )

    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    
    crop_hint: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    analyses: Mapped[list["ImageAnalysis"]] = relationship(
        "ImageAnalysis", back_populates="image", cascade="all, delete-orphan"
    )
