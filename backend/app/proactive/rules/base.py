"""Base interface and data contracts for the Proactive Relevance & Rule Engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.events.contracts import EventEnvelope
from app.models.proactive import RiskSeverity


@dataclass(frozen=True, slots=True)
class RuleResult:
    """Outcome of evaluating a relevance rule against an event and agricultural context."""

    matched: bool
    rule_id: str
    risk_type: str
    severity: RiskSeverity = RiskSeverity.LOW
    confidence: float = 1.0
    reason: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    recommended_action_summary: str = ""


class BaseRelevanceRule(ABC):
    """Abstract base class for modular agricultural relevance rules."""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Unique identifier for the rule."""

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Human-readable name of the rule."""

    @property
    @abstractmethod
    def supported_events(self) -> list[str]:
        """List of event types this rule evaluates."""

    @abstractmethod
    async def evaluate(self, event: EventEnvelope, context: dict[str, Any]) -> RuleResult:
        """Evaluate if the event is relevant and risky for the given farmer/field context."""
