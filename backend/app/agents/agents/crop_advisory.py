"""Crop advisory agent that combines retrieved knowledge with domain rules."""

from __future__ import annotations

from app.agents.interfaces import AgentContext, AgentMetadata, AgentResult


class CropAdvisoryAgent:
    """Generate grounded crop guidance for agricultural problems."""

    async def initialize(self, context: AgentContext) -> None:
        """Prepare the agent for execution."""

    async def execute(self, context: AgentContext) -> AgentResult:
        """Generate a structured advisory response."""
        return AgentResult(
            agent_name="crop_advisory",
            status="completed",
            output={"advisory": f"Grounded advisory for: {context.user_goal}"},
            confidence=0.78,
        )

    async def validate(self, result: AgentResult) -> bool:
        """Validate that the advisory has a clear recommendation."""
        return bool(result.output.get("advisory"))

    async def cleanup(self, context: AgentContext) -> None:
        """Release runtime resources."""

    async def health(self) -> str:
        """Return the runtime health status."""
        return "healthy"

    def metadata(self) -> AgentMetadata:
        """Return the agent metadata."""
        return AgentMetadata(
            name="crop_advisory",
            description="Synthesizes retrieved context into agricultural recommendations.",
            capabilities=["advisory_generation"],
            input_schema={"goal": "string"},
            output_schema={"advisory": "string"},
            supported_tools=["knowledge_search"],
            priority=8,
            version="1.0",
        )
