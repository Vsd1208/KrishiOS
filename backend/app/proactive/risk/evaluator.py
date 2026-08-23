"""Risk Assessment Evaluator synthesizing rule results and multi-source context."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.events.contracts import EventEnvelope
from app.models.proactive import RiskSeverity
from app.proactive.context import FarmerFieldContext
from app.proactive.risk.models import EvidencePackage, RiskAssessment
from app.proactive.rules.base import RuleResult

_SEVERITY_ORDER = {
    RiskSeverity.LOW: 1,
    RiskSeverity.MEDIUM: 2,
    RiskSeverity.HIGH: 3,
    RiskSeverity.CRITICAL: 4,
}


class RiskEvaluator:
    """Synthesizes matched agricultural rules and contextual data into an actionable RiskAssessment."""

    def evaluate(
        self,
        event: EventEnvelope,
        context: FarmerFieldContext,
        rule_results: list[RuleResult],
    ) -> RiskAssessment | None:
        """Combine matched rules and build an auditable RiskAssessment."""
        if not rule_results:
            return None

        # Determine highest severity among matched rules
        sorted_results = sorted(
            rule_results, key=lambda r: _SEVERITY_ORDER.get(r.severity, 1), reverse=True
        )
        primary_result = sorted_results[0]

        highest_severity = primary_result.severity
        active_rules = [r.rule_id for r in rule_results]
        rule_reasons = [r.reason for r in rule_results]
        
        # Calculate composite confidence
        confidences = [r.confidence for r in rule_results]
        avg_confidence = sum(confidences) / len(confidences)

        # Check for stale data (e.g. event older than 72 hours)
        now = datetime.now(UTC)
        event_age_seconds = int((now - event.timestamp).total_seconds())
        if event_age_seconds > 259200: # 72 hours
            avg_confidence *= 0.5

        # Format complete evidence package
        evidence_pkg = EvidencePackage(
            live_telemetry={
                "weather": context.live_weather,
                "advisory": context.live_advisory,
                "market": context.live_market,
                "event_payload": event.payload,
            },
            rag_citations=context.vector_rag_snippets,
            graph_paths=context.graph_knowledge_paths,
            vision_findings=context.recent_vision_findings,
            active_rules=active_rules,
            rule_reasons=rule_reasons,
            data_freshness_seconds=event_age_seconds,
            confidence_breakdown={
                "rule_confidence": primary_result.confidence,
                "composite_confidence": avg_confidence,
                "event_age_penalty": 0.5 if event_age_seconds > 259200 else 1.0,
            },
        )

        # Human-in-the-loop policy:
        # High impact (CRITICAL / HIGH) with confidence < 0.80 -> requires human review
        requires_review = (
            highest_severity in [RiskSeverity.HIGH, RiskSeverity.CRITICAL]
            and avg_confidence < 0.80
        )

        # Valid until duration based on risk type
        validity_hours = 24 if highest_severity == RiskSeverity.CRITICAL else 48

        return RiskAssessment(
            risk_type=primary_result.risk_type,
            severity=highest_severity,
            probability=min(1.0, float(event.payload.get("probability", 0.85))),
            confidence=round(avg_confidence, 2),
            farmer_id=context.farmer_id,
            field_id=context.field_id,
            crop=context.crop_name,
            evidence_package=evidence_pkg,
            recommended_action=primary_result.recommended_action_summary,
            requires_human_review=requires_review,
            valid_until=now + timedelta(hours=validity_hours),
        )
