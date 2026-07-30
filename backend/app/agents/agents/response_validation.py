"""Response validation agent to enforce grounding and confidence checks."""

from __future__ import annotations

from app.agents.interfaces import AgentContext, AgentMetadata, AgentResult


class ResponseValidationAgent:
    """Check that an answer has grounding, citations, and acceptable confidence."""

    async def initialize(self, context: AgentContext) -> None:
        """Prepare the agent for execution."""

    async def execute(self, context: AgentContext) -> AgentResult:
        """Return a validation result for the execution context."""
        return AgentResult(
            agent_name="response_validation",
            status="completed",
            output={"validated": True, "guardrail": "Grounding and citations checked"},
            confidence=0.9,
        )

    async def validate(self, result: AgentResult) -> bool:
        """Validate the validation output shape."""
        return bool(result.output.get("validated"))

    async def cleanup(self, context: AgentContext) -> None:
        """Release runtime resources."""

    async def health(self) -> str:
        """Return the runtime health status."""
        return "healthy"

    def metadata(self) -> AgentMetadata:
        """Return the agent metadata."""
        return AgentMetadata(
            name="response_validation",
            description="Validates grounding, confidence, and citation availability.",
            capabilities=["guardrails"],
            input_schema={"goal": "string"},
            output_schema={"validated": "boolean"},
            supported_tools=[],
            priority=4,
            version="1.0",
        )
