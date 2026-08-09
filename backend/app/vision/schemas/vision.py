"""Pydantic schemas for the vision API endpoints."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

from app.vision.models.analysis import ImageAnalysisStatus, ReviewStatus


class ImageUploadRequest(BaseModel):
    """Metadata payload accompanying an image upload."""
    crop_hint: str | None = Field(default=None, description="Optional crop hint from user")
    field_uuid: UUID | None = Field(default=None, description="Optional field UUID this image belongs to")


class ImageUploadResponse(BaseModel):
    """Response returned immediately after 202 Accepted upload."""
    image_id: int
    uuid: UUID
    status: ImageAnalysisStatus


class ObservationSchema(BaseModel):
    finding: str
    confidence: float
    bbox: tuple[int, int, int, int] | None = None


class CandidateConditionSchema(BaseModel):
    name: str
    confidence: float


class AnalysisResponse(BaseModel):
    """Detailed analysis results."""
    id: int
    uuid: UUID
    image_uuid: UUID
    model_name: str
    model_version: str
    status: ImageAnalysisStatus
    quality_score: float | None = None
    quality_issues: list[str] | None = None
    crop_detected: str | None = None
    observations: list[ObservationSchema] = Field(default_factory=list)
    candidate_conditions: list[CandidateConditionSchema] = Field(default_factory=list)
    confidence_score: float | None = None
    review_status: ReviewStatus
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class AnalysisListResponse(BaseModel):
    """Paginated list of analyses."""
    total: int
    offset: int
    limit: int
    items: list[AnalysisResponse]
