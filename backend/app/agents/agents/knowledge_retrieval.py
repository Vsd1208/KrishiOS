"""Knowledge retrieval agent using the Sprint 3 retrieval platform."""

from __future__ import annotations

from app.agents.interfaces import AgentContext, AgentMetadata, AgentResult
from app.agents.tools.knowledge_search import KnowledgeSearchTool


class KnowledgeRetrievalAgent:
    """Retrieve grounded knowledge for agricultural reasoning tasks."""

    def __init__(self, tool: KnowledgeSearchTool) -> None:
        self._tool = tool

    async def initialize(self, context: AgentContext) -> None:
        """Prepare the agent for execution."""

    async def execute(self, context: AgentContext) -> AgentResult:
        """Search the enterprise retrieval platform for relevant agricultural knowledge."""
        result = await self._tool.run(context.user_goal)
        return AgentResult(
            agent_name="knowledge_retrieval",
            status="completed",
            output={"knowledge": result},
            confidence=0.84,
            citations=[{"source": item["citation"]["source"]} for item in result.get("results", [])],
        )

    async def validate(self, result: AgentResult) -> bool:
        """Validate that the retrieval returned enough grounded context."""
        return bool(result.output.get("knowledge", {}).get("results"))

    async def cleanup(self, context: AgentContext) -> None:
        """Release runtime resources."""

    async def health(self) -> str:
        """Return the runtime health status."""
        return "healthy"

    def metadata(self) -> AgentMetadata:
        """Return the agent metadata."""
        return AgentMetadata(
            name="knowledge_retrieval",
            description="Retrieves grounded agricultural knowledge from the enterprise retrieval platform.",
            capabilities=["knowledge_search"],
            input_schema={"goal": "string"},
            output_schema={"knowledge": "object"},
            supported_tools=["knowledge_search"],
            priority=10,
            version="1.0",
        )
