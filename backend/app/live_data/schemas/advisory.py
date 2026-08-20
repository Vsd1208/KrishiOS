"""Normalized agricultural advisory schemas."""

from datetime import datetime
from enum import Enum
from pydantic import Field

from app.live_data.schemas.common import BaseLiveDataResponse


class AdvisoryStatus(str, Enum):
    """Advisory validity status."""

    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"


class AgriculturalAdvisory(BaseLiveDataResponse):
    """Normalized agromet or crop advisory from ICAR/State Dept."""

    advisory_id: str
    title: str
    content: str
    crop: str
    state: str
    district: str | None = None
    issuing_authority: str
    effective_from: datetime
    effective_until: datetime
    status: AdvisoryStatus = AdvisoryStatus.ACTIVE
    superseded_by_id: str | None = None
    recommended_practices: list[str] = Field(default_factory=list)
    warning_notes: list[str] = Field(default_factory=list)
