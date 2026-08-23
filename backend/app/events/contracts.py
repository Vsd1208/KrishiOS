"""Typed Event Contracts and Envelopes for KrishiOS Event-Driven Architecture."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class EventType(StrEnum):
    """Standard event types supported by KrishiOS."""

    # ── Weather Events ────────────────────────────────────────────────────────
    WEATHER_ALERT = "weather.alert"
    HEAVY_RAIN_EXPECTED = "weather.heavy_rain"
    EXTREME_HEAT = "weather.extreme_heat"
    HIGH_HUMIDITY = "weather.high_humidity"

    # ── Agronomic & Biological Events ─────────────────────────────────────────
    DISEASE_RISK_CHANGED = "agronomy.disease_risk_changed"
    PEST_RISK_DETECTED = "agronomy.pest_risk_detected"
    FIELD_ANALYSIS_COMPLETED = "agronomy.field_analysis_completed"
    VISION_RISK_DETECTED = "vision.risk_detected"

    # ── Economic & Market Events ──────────────────────────────────────────────
    MARKET_PRICE_CHANGED = "market.price_changed"
    PRICE_ANOMALY_DETECTED = "market.price_anomaly"

    # ── Government & Institutional Events ─────────────────────────────────────
    AGRICULTURAL_ADVISORY_UPDATED = "advisory.updated"
    GOVERNMENT_SCHEME_UPDATED = "scheme.updated"

    # ── Knowledge & System Events ─────────────────────────────────────────────
    KNOWLEDGE_INDEX_UPDATED = "knowledge.index_updated"
    SYSTEM_ALERT = "system.alert"


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    """Standard immutable envelope for all internal and external events in KrishiOS."""

    event_type: str
    payload: dict[str, Any]
    event_id: UUID = field(default_factory=uuid4)
    source: str = "internal"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = "1.0.0"
    correlation_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert envelope to serializable dictionary."""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "schema_version": self.schema_version,
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "payload": self.payload,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventEnvelope:
        """Construct envelope from dictionary representation."""
        return cls(
            event_id=UUID(data["event_id"]) if isinstance(data.get("event_id"), str) else (data.get("event_id") or uuid4()),
            event_type=data["event_type"],
            source=data.get("source", "internal"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data.get("timestamp"), str) else data.get("timestamp", datetime.now(UTC)),
            schema_version=data.get("schema_version", "1.0.0"),
            correlation_id=UUID(data["correlation_id"]) if isinstance(data.get("correlation_id"), str) else data.get("correlation_id"),
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {}),
        )
