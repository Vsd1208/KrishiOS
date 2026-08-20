"""Normalized Government Welfare Scheme schemas."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from app.live_data.schemas.common import BaseLiveDataResponse


class SchemeEligibility(str, Enum):
    """Eligibility status."""

    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    PARTIALLY_ELIGIBLE = "PARTIALLY_ELIGIBLE"
    UNKNOWN = "UNKNOWN"


class GovernmentScheme(BaseLiveDataResponse):
    """Normalized central/state agricultural scheme."""

    scheme_id: str
    name: str
    description: str
    state: str | None = None  # None indicates Central scheme (e.g. PM-KISAN, PMFBY)
    target_crops: list[str] = Field(default_factory=list)
    max_landholding_acres: float | None = None
    farmer_categories: list[str] = Field(default_factory=list)  # ["Small", "Marginal", "Tenant", "Women"]
    benefits: str
    subsidy_amount_or_percent: str
    application_process: str
    official_portal_url: str
    last_verified_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "Active"


class SchemeEligibilityEvaluation(BaseModel):
    """Farmer eligibility evaluation against a specific scheme."""

    scheme: GovernmentScheme
    eligibility: SchemeEligibility
    reason: str
    missing_criteria: list[str] = Field(default_factory=list)
