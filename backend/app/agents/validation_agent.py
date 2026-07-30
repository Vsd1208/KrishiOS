"""Response Validation Agent evaluating grounding, confidence, and safety rules."""

from time import perf_counter
from typing import Any

from loguru import logger

from app.agents.base import AgentMetadata, BaseAgent
from app.agents.execution.context import AgentStatus, AgentStepTrace, ExecutionContext, ExecutionResult
from app.agents.security.guardrails import GuardrailEngine


class ResponseValidationAgent(BaseAgent):
    """Production Response Validation Agent checking grounding, safety, and citations."""

    def __init__(self, guardrail_engine: GuardrailEngine) -> None:
        metadata = AgentMetadata(
            name="response_validation_agent",
            description="Evaluates grounding, source citations, confidence scores, and safety rules.",
            capabilities=["validation", "guardrail", "grounding_check"],
            input_schema={"output_text": "string", "confidence_score": "float", "citations": "list"},
            output_schema={"passed": "boolean", "safe_output": "string"},
            supported_tools=[],
            priority=5,
            version="1.0.0",
        )
        super().__init__(metadata)
        self._guardrails = guardrail_engine

    async def initialize(self) -> None:
        self._status = AgentStatus.IDLE
        logger.info("ResponseValidationAgent: initialized")

    async def execute(
        self,
        task: str,
        context: ExecutionContext,
        parameters: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        t0 = perf_counter()
        self._status = AgentStatus.RUNNING

        params = parameters or {}
        output_text = str(params.get("output_text", task))
        confidence = float(params.get("confidence_score", 0.8))
        citations = params.get("citations", [])
        require_citations = bool(params.get("require_citations", False))

        res = self._guardrails.evaluate(
            output_text=output_text,
            confidence_score=confidence,
            citations=citations,
            require_citations=require_citations,
        )

        duration_ms = (perf_counter() - t0) * 1000
        trace = AgentStepTrace(
            step_number=len(context.traces) + 1,
            agent_name=self.metadata.name,
            action="evaluate_guardrails",
            input_data={"confidence": confidence, "citations_count": len(citations)},
            output_data={"passed": res.passed, "rejection_reason": res.rejection_reason},
            duration_ms=duration_ms,
        )
        context.add_trace(trace)

        self._status = AgentStatus.COMPLETED
        return ExecutionResult(
            execution_id=context.execution_id,
            status=AgentStatus.COMPLETED,
            agent_name=self.metadata.name,
            output={
                "passed": res.passed,
                "validated_text": res.safe_output,
                "rejection_reason": res.rejection_reason,
            },
            confidence_score=res.confidence_score,
            grounded=res.grounded,
            citations=citations,
            traces=[trace],
            duration_ms=duration_ms,
        )

    async def validate(self, result: ExecutionResult) -> bool:
        return result.status == AgentStatus.COMPLETED

    async def cleanup(self) -> None:
        self._status = AgentStatus.IDLE

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "agent": self.metadata.name}
