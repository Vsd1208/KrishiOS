"""Proactive Intelligence Agent for generating grounded, explainable agricultural alerts."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from loguru import logger

from app.agents.base import AgentMetadata, BaseAgent
from app.agents.execution.context import (
    AgentStatus,
    AgentStepTrace,
    ExecutionContext,
    ExecutionResult,
)
from app.agents.providers.llm import LLMProvider


class ProactiveIntelligenceAgent(BaseAgent):
    """Generates explainable, evidence-grounded proactive agricultural advisories."""

    def __init__(self, llm_provider: LLMProvider) -> None:
        metadata = AgentMetadata(
            name="proactive_intelligence_agent",
            description=(
                "Synthesizes actionable, evidence-grounded proactive advisories "
                "from event anomalies, risk assessments, and multi-source telemetry."
            ),
            capabilities=["proactive_advisory", "risk_explanation", "evidence_synthesis"],
            input_schema={"risk_type": "string", "severity": "string", "crop": "string"},
            output_schema={"advisory": "string", "explanation": "string", "citations": "list"},
            supported_tools=["knowledge_search", "knowledge_graph_search", "live_weather"],
            priority=25,
            version="1.0.0",
        )
        super().__init__(metadata)
        self._llm = llm_provider

    async def initialize(self) -> None:
        self._status = AgentStatus.IDLE
        logger.info("ProactiveIntelligenceAgent: initialized")

    async def execute(
        self,
        task: str,
        context: ExecutionContext,
        parameters: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        t0 = perf_counter()
        self._status = AgentStatus.RUNNING

        params = parameters or {}
        risk_type = params.get("risk_type", "general_advisory")
        severity = params.get("severity", "MEDIUM")
        confidence = float(params.get("confidence", 0.85))
        crop = params.get("crop") or context.crop or "standing crop"
        district = params.get("district") or context.district or "your region"
        state = params.get("state") or context.state or "India"
        rules_matched = params.get("rules_matched", [])
        evidence_summary = params.get("evidence_summary", "")
        recommended_action = params.get("recommended_action", "")
        citations = params.get("citations", [])

        prompt = (
            f"Event Risk Assessment:\n"
            f"- Risk Type: {risk_type}\n"
            f"- Severity: {severity}\n"
            f"- Confidence: {confidence:.2f}\n"
            f"- Location: {district}, {state}\n"
            f"- Target Crop: {crop}\n"
            f"- Matched Rules: {', '.join(rules_matched) if rules_matched else 'Threshold triggered'}\n"
            f"- Evidence & Knowledge Base: {evidence_summary}\n"
            f"- Core Agronomic Directive: {recommended_action}\n\n"
            f"Instructions:\n"
            f"Generate a clear, respectful, and actionable advisory message for the farmer.\n"
            f"Structure your response with:\n"
            f"1. Alert Summary: State the situation and severity directly.\n"
            f"2. Crop Impact: Explain why this matters for {crop}.\n"
            f"3. Recommended Action: Give clear, concrete steps the farmer should take.\n"
            f"4. Source & Freshness: Explicitly cite where this information came from (e.g. IMD, ICAR, Agromet Advisory).\n"
            f"Never invent scientific facts or guarantee crop failure. State any uncertainty clearly."
        )

        system_instruction = (
            "You are KrishiOS Proactive Decision Support AI. You provide calm, accurate, "
            "authoritative, and evidence-grounded agricultural advisories to Indian farmers."
        )

        llm_resp = await self._llm.generate(
            prompt=prompt,
            system_instruction=system_instruction,
        )

        duration_ms = (perf_counter() - t0) * 1000
        trace = AgentStepTrace(
            step_number=len(context.traces) + 1,
            agent_name=self.metadata.name,
            action="synthesize_proactive_advisory",
            input_data={"risk_type": risk_type, "severity": severity, "crop": crop},
            output_data={"tokens": llm_resp.total_tokens, "confidence": confidence},
            duration_ms=duration_ms,
        )
        context.add_trace(trace)

        self._status = AgentStatus.COMPLETED
        return ExecutionResult(
            execution_id=context.execution_id,
            status=AgentStatus.COMPLETED,
            agent_name=self.metadata.name,
            output={
                "advisory": llm_resp.content,
                "risk_type": risk_type,
                "severity": severity,
                "confidence": confidence,
                "crop": crop,
            },
            confidence_score=confidence,
            grounded=True,
            citations=citations,
            traces=[trace],
            duration_ms=duration_ms,
        )

    async def validate(self, result: ExecutionResult) -> bool:
        return result.status == AgentStatus.COMPLETED and result.confidence_score >= 0.3

    async def cleanup(self) -> None:
        self._status = AgentStatus.IDLE

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "agent": self.metadata.name, "llm": self._llm.provider_name}
