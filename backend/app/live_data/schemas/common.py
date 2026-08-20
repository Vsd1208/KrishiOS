"""Common primitives, freshness states, and source authority levels for live data."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class FreshnessStatus(str, Enum):
    """Data freshness lifecycle states."""

    FRESH = "FRESH"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    UNAVAILABLE = "UNAVAILABLE"


class SourceAuthorityLevel(str, Enum):
    """Source authority hierarchy for grounding confidence."""

    GOVERNMENT = "GOVERNMENT"                      # e.g., IMD, MoA&FW (Score: 1.0)
    ICAR = "ICAR"                                  # e.g., ICAR-CRIDA, IARI (Score: 0.95)
    AGRICULTURAL_UNIVERSITY = "AGRICULTURAL_UNIVERSITY"  # e.g., PJTSAU, TNAU (Score: 0.90)
    AUTHORIZED_OFFICER = "AUTHORIZED_OFFICER"      # e.g., District Agriculture Officer (Score: 0.85)
    VERIFIED_EXTERNAL_PROVIDER = "VERIFIED_EXTERNAL_PROVIDER"  # e.g., Open-Meteo, Agmarknet API (Score: 0.75)
    UNVERIFIED_EXTERNAL_SOURCE = "UNVERIFIED_EXTERNAL_SOURCE"  # e.g., Web scrape (Score: 0.40)


class BaseLiveDataResponse(BaseModel):
    """Base schema for all live data responses preserving provenance and freshness."""

    response_id: UUID = Field(default_factory=uuid4)
    provider_name: str
    provider_version: str = "1.0.0"
    source: str
    authority_level: SourceAuthorityLevel = SourceAuthorityLevel.VERIFIED_EXTERNAL_PROVIDER
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid_until: datetime | None = None
    freshness: FreshnessStatus = FreshnessStatus.FRESH
    cached: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
