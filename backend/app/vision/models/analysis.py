"""ImageAnalysis model for tracking vision model results and lifecycle."""

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.core import Base
from app.models.base import TimestampMixin


class ImageAnalysisStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    VALIDATING = "VALIDATING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class ReviewStatus(str, enum.Enum):
    AI_SUGGESTED = "AI_SUGGESTED"
    OFFICER_REVIEWED = "OFFICER_REVIEWED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class ImageAnalysis(TimestampMixin, Base):
    """Tracks the lifecycle and results of a vision model analysis."""

    __tablename__ = "image_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        default=uuid4,
        unique=True,
        nullable=False,
        index=True,
    )
    
    image_id: Mapped[int] = mapped_column(
        ForeignKey("crop_images.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    
    status: Mapped[ImageAnalysisStatus] = mapped_column(
        String(50), nullable=False, default=ImageAnalysisStatus.UPLOADED, index=True
    )
    
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_issues: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    
    findings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    review_status: Mapped[ReviewStatus] = mapped_column(
        String(50), nullable=False, default=ReviewStatus.AI_SUGGESTED
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user.uuid", ondelete="SET NULL"), nullable=True
    )
    
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    image: Mapped["CropImage"] = relationship("CropImage", back_populates="analyses")
