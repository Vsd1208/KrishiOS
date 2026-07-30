"""Knowledge Retrieval Agent leveraging Sprint 3 Enterprise Retrieval Platform."""

from time import perf_counter
from typing import Any

from loguru import logger

from app.agents.base import AgentMetadata, BaseAgent
from app.agents.execution.context import AgentStatus, AgentStepTrace, ExecutionContext, ExecutionResult
from app.agents.tools.knowledge_search import KnowledgeSearchTool


class KnowledgeRetrievalAgent(BaseAgent):
    """Production Knowledge Retrieval Agent using Sprint 3 RAG platform."""

    def __init__(self, search_tool: KnowledgeSearchTool) -> None:
        metadata = AgentMetadata(
            name="knowledge_retrieval_agent",
            description="Searches verified ICAR research, government circulars, and agricultural advisories.",
            capabilities=["retrieval", "search", "rag"],
            input_schema={"query": "string", "crop": "string", "state": "string"},
            output_schema={"chunks": "list", "total_hits": "integer"},
            supported_tools=["knowledge_search"],
            priority=10,
            version="1.0.0",
        )
        super().__init__(metadata)
        self._search_tool = search_tool

    async def initialize(self) -> None:
        self._status = AgentStatus.IDLE
        logger.info("KnowledgeRetrievalAgent: initialized")

    async def execute(
        self,
        task: str,
        context: ExecutionContext,
        parameters: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        t0 = perf_counter()
        self._status = AgentStatus.RUNNING

        params = parameters or {}
        query = params.get("query", task)

        tool_result = await self._search_tool.execute({
            "query": query,
            "crop": params.get("crop") or context.crop,
            "state": params.get("state") or context.state,
            "district": params.get("district") or context.district,
            "season": params.get("season") or context.season,
            "top_k": params.get("top_k", 5),
        })

        duration_ms = (perf_counter() - t0) * 1000

        trace = AgentStepTrace(
            step_number=len(context.traces) + 1,
            agent_name=self.metadata.name,
            action="execute_knowledge_search",
            input_data={"query": query},
            output_data={"success": tool_result.success, "hits": tool_result.data.get("total_hits", 0)},
            duration_ms=duration_ms,
        )
        context.add_trace(trace)

        if not tool_result.success:
            self._status = AgentStatus.FAILED
            return ExecutionResult(
                execution_id=context.execution_id,
                status=AgentStatus.FAILED,
                agent_name=self.metadata.name,
                output={},
                confidence_score=0.0,
                grounded=False,
                duration_ms=duration_ms,
                error_message=tool_result.error_message,
            )

        hits = tool_result.data.get("hits", [])
        top_score = hits[0].get("score", 0.0) if hits else 0.0
        citations = [h.get("citation") for h in hits if h.get("citation")]

        self._status = AgentStatus.COMPLETED
        return ExecutionResult(
            execution_id=context.execution_id,
            status=AgentStatus.COMPLETED,
            agent_name=self.metadata.name,
            output=tool_result.data,
            confidence_score=float(top_score),
            grounded=len(hits) > 0,
            citations=citations,
            traces=[trace],
            duration_ms=duration_ms,
        )

    async def validate(self, result: ExecutionResult) -> bool:
        return result.status == AgentStatus.COMPLETED and result.grounded

    async def cleanup(self) -> None:
        self._status = AgentStatus.IDLE

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "agent": self.metadata.name, "tool": self._search_tool.metadata.name}
