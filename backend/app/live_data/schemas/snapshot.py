"""Decision data snapshot for reproducible decision intelligence audits."""

from datetime import UTC, datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class DecisionDataSnapshot(BaseModel):
    """Immutable record capturing live telemetry used in generating a specific advisory decision."""

    snapshot_id: UUID = Field(default_factory=uuid4)
    execution_id: UUID
    user_uuid: UUID
    field_id: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    weather_response_id: UUID | None = None
    weather_observed_at: datetime | None = None
    weather_freshness: str | None = None

    market_response_id: UUID | None = None
    market_modal_price: float | None = None
    market_freshness: str | None = None

    advisory_id: str | None = None
    advisory_authority: str | None = None

    agent_version: str = "1.0.0"
    model_version: str = "1.0.0"
    snapshot_hash: str = ""
