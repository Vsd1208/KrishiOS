"""Event Processor orchestrating event validation, deduplication, context, rules, and decision workflows."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.execution.context import AgentStatus, ExecutionContext
from app.agents.proactive_agent import ProactiveIntelligenceAgent
from app.agents.runtime.engine import AgentRuntimeEngine
from app.events.contracts import EventEnvelope
from app.models.proactive import (
    AlertPriority,
    ProactiveDecisionRecord,
    ProactiveEventRecord,
    RiskSeverity,
)
from app.notifications.service import NotificationService
from app.proactive.context import ProactiveContextEngine
from app.proactive.deduplication import EventDeduplicator
from app.proactive.risk.evaluator import RiskEvaluator
from app.proactive.rules.agricultural_rules import RuleRegistry


class EventProcessor:
    """Central processing engine for agricultural events."""

    def __init__(
        self,
        deduplicator: EventDeduplicator,
        context_engine: ProactiveContextEngine,
        rule_registry: RuleRegistry,
        risk_evaluator: RiskEvaluator,
        notification_service: NotificationService,
        runtime_engine: AgentRuntimeEngine | None = None,
        proactive_agent: ProactiveIntelligenceAgent | None = None,
    ) -> None:
        self._deduplicator = deduplicator
        self._context_engine = context_engine
        self._rule_registry = rule_registry
        self._risk_evaluator = risk_evaluator
        self._notification_service = notification_service
        self._runtime_engine = runtime_engine
        self._proactive_agent = proactive_agent

    async def process_event(
        self, session: AsyncSession, event: EventEnvelope
    ) -> list[ProactiveDecisionRecord]:
        """Process an incoming event through the complete decision pipeline."""
        fingerprint = self._deduplicator.compute_event_fingerprint(event)

        # 1. Record event in database
        event_record = ProactiveEventRecord(
            event_id=event.event_id,
            event_type=event.event_type,
            source=event.source,
            fingerprint=fingerprint,
            payload=event.payload,
            status="RECEIVED",
        )
        session.add(event_record)
        await session.flush()

        # 2. Check event deduplication
        is_duplicate = await self._deduplicator.is_duplicate_event(event)
        if is_duplicate:
            event_record.status = "DUPLICATE"
            await session.flush()
            logger.info("EventProcessor: duplicate event {} suppressed", event.event_id)
            return []

        # 3. Collect affected contexts
        contexts = await self._context_engine.collect_contexts_for_event(event)
        if not contexts:
            event_record.status = "NO_TARGETS"
            await session.flush()
            logger.debug("EventProcessor: no target farmers found for event {}", event.event_id)
            return []

        decisions: list[ProactiveDecisionRecord] = []

        for ctx in contexts:
            eval_dict = ctx.to_evaluation_context()
            matched_rules = await self._rule_registry.evaluate_all(event, eval_dict)
            if not matched_rules:
                continue

            # 4. Assess risk and build evidence package
            risk = self._risk_evaluator.evaluate(event, ctx, matched_rules)
            if risk is None:
                continue

            # 5. Synthesize advisory via Proactive Intelligence Agent (LLM invoked only when qualified)
            advisory_text = risk.recommended_action
            if self._proactive_agent is not None:
                try:
                    exec_ctx = ExecutionContext(
                        execution_id=uuid4(),
                        crop=ctx.crop_name,
                        district=ctx.district_name,
                        state=ctx.state_name,
                    )
                    evidence_str = "; ".join(
                        risk.evidence_package.rag_citations + risk.evidence_package.graph_paths
                    )
                    agent_res = await self._proactive_agent.execute(
                        task=f"Generate proactive advisory for {risk.risk_type}",
                        context=exec_ctx,
                        parameters={
                            "risk_type": risk.risk_type,
                            "severity": risk.severity.value,
                            "confidence": risk.confidence,
                            "crop": ctx.crop_name,
                            "district": ctx.district_name,
                            "state": ctx.state_name,
                            "rules_matched": risk.evidence_package.active_rules,
                            "evidence_summary": evidence_str or "Authoritative agronomic guidelines",
                            "recommended_action": risk.recommended_action,
                            "citations": risk.evidence_package.rag_citations,
                        },
                    )
                    if agent_res.status == AgentStatus.COMPLETED and "advisory" in agent_res.output:
                        advisory_text = agent_res.output["advisory"]
                except Exception as exc:
                    logger.warning("EventProcessor: proactive agent synthesis fallback: {}", exc)

            # 6. Save Decision Record
            decision = ProactiveDecisionRecord(
                decision_id=uuid4(),
                event_id=event.event_id,
                farmer_id=ctx.farmer_id,
                field_id=ctx.field_id,
                risk_type=risk.risk_type,
                risk_severity=risk.severity,
                confidence=risk.confidence,
                evidence_package=risk.evidence_package.to_dict(),
                workflow_version="1.0.0",
                agent_version="1.0.0",
                advisory_text=advisory_text,
                requires_review=risk.requires_human_review,
                valid_until=risk.valid_until,
            )
            session.add(decision)
            await session.flush()
            decisions.append(decision)

            # 7. Dispatch or queue notification
            priority = (
                AlertPriority.URGENT
                if risk.severity == RiskSeverity.CRITICAL
                else (AlertPriority.HIGH if risk.severity == RiskSeverity.HIGH else AlertPriority.NORMAL)
            )

            title = f"Agricultural Alert: {risk.risk_type.replace('_', ' ').title()}"
            await self._notification_service.dispatch_alert(
                session=session,
                farmer_id=ctx.farmer_id,
                title=title,
                message=advisory_text,
                alert_type=risk.risk_type,
                topic_key=f"{risk.risk_type}:{ctx.crop_name or 'crop'}",
                severity=risk.severity,
                priority=priority,
                decision_id=decision.id,
                requires_review=risk.requires_human_review,
            )

        event_record.status = "PROCESSED"
        await session.flush()
        return decisions
