"""Data contracts for Risk Assessment and Evidence Packages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from app.models.proactive import RiskSeverity


@dataclass(frozen=True, slots=True)
class EvidencePackage:
    """Comprehensive, auditable evidence trail supporting a proactive recommendation."""

    live_telemetry: dict[str, Any] = field(default_factory=dict)
    rag_citations: list[str] = field(default_factory=list)
    graph_paths: list[str] = field(default_factory=list)
    vision_findings: list[dict[str, Any]] = field(default_factory=list)
    active_rules: list[str] = field(default_factory=list)
    rule_reasons: list[str] = field(default_factory=list)
    rule_version: str = "1.0.0"
    model_version: str = "1.0.0"
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    data_freshness_seconds: int = 0
    confidence_breakdown: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert evidence package to dictionary."""
        return {
            "live_telemetry": self.live_telemetry,
            "rag_citations": self.rag_citations,
            "graph_paths": self.graph_paths,
            "vision_findings": self.vision_findings,
            "active_rules": self.active_rules,
            "rule_reasons": self.rule_reasons,
            "rule_version": self.rule_version,
            "model_version": self.model_version,
            "generated_at": self.generated_at,
            "data_freshness_seconds": self.data_freshness_seconds,
            "confidence_breakdown": self.confidence_breakdown,
        }


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    """Structured evaluation of agricultural risk, probability, and confidence."""

    risk_type: str
    severity: RiskSeverity
    probability: float
    confidence: float
    farmer_id: int
    field_id: int | None
    crop: str | None
    evidence_package: EvidencePackage
    recommended_action: str
    requires_human_review: bool = False
    valid_until: datetime = field(
        default_factory=lambda: datetime.now(UTC) + timedelta(hours=48)
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert assessment to dictionary."""
        return {
            "risk_type": self.risk_type,
            "severity": self.severity.value,
            "probability": self.probability,
            "confidence": self.confidence,
            "farmer_id": self.farmer_id,
            "field_id": self.field_id,
            "crop": self.crop,
            "evidence_package": self.evidence_package.to_dict(),
            "recommended_action": self.recommended_action,
            "requires_human_review": self.requires_human_review,
            "valid_until": self.valid_until.isoformat(),
        }
