"""Government Scheme Agent for subsidy, welfare, and insurance guidance."""

from time import perf_counter
from typing import Any

from loguru import logger

from app.agents.base import AgentMetadata, BaseAgent
from app.agents.execution.context import AgentStatus, AgentStepTrace, ExecutionContext, ExecutionResult
from app.agents.providers.llm import LLMProvider
from app.agents.tools.knowledge_search import KnowledgeSearchTool


class GovtSchemeAgent(BaseAgent):
    """Production Government Scheme Agent for PM-KISAN, PMFBY, and state schemes."""

    def __init__(self, llm_provider: LLMProvider, search_tool: KnowledgeSearchTool) -> None:
        metadata = AgentMetadata(
            name="govt_scheme_agent",
            description="Explains government agricultural schemes, eligibility criteria, and application steps.",
            capabilities=["government_schemes", "subsidies", "crop_insurance", "pm_kisan"],
            input_schema={"query": "string", "state": "string"},
            output_schema={"scheme_details": "string", "citations": "list"},
            supported_tools=["knowledge_search", "government_db"],
            priority=30,
            version="1.0.0",
        )
        super().__init__(metadata)
        self._llm = llm_provider
        self._search_tool = search_tool

    async def initialize(self) -> None:
        self._status = AgentStatus.IDLE
        logger.info("GovtSchemeAgent: initialized")

    async def execute(
        self,
        task: str,
        context: ExecutionContext,
        parameters: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        t0 = perf_counter()
        self._status = AgentStatus.RUNNING

        search_res = await self._search_tool.execute({
            "query": f"Government scheme subsidy {task}",
            "state": context.state,
            "top_k": 3,
        })

        hits = search_res.data.get("hits", [])
        context_str = "\n---\n".join([h.get("chunk_text", "") for h in hits])
        citations = [h.get("citation") for h in hits if h.get("citation")]

        prompt = (
            f"Farmer Query: {task}\nState: {context.state or 'India'}\n"
            f"Official Scheme Circulars:\n{context_str}\n\n"
            "Explain the scheme benefits, eligibility criteria, and enrollment process clearly."
        )

        llm_resp = await self._llm.generate(
            prompt=prompt,
            system_instruction="You are an official Ministry of Agriculture advisor detailing government welfare schemes.",
        )

        duration_ms = (perf_counter() - t0) * 1000
        trace = AgentStepTrace(
            step_number=len(context.traces) + 1,
            agent_name=self.metadata.name,
            action="explain_scheme",
            input_data={"task": task},
            output_data={"tokens": llm_resp.total_tokens},
            duration_ms=duration_ms,
        )
        context.add_trace(trace)

        confidence = float(hits[0].get("score", 0.7)) if hits else 0.5

        self._status = AgentStatus.COMPLETED
        return ExecutionResult(
            execution_id=context.execution_id,
            status=AgentStatus.COMPLETED,
            agent_name=self.metadata.name,
            output={
                "scheme_details": llm_resp.content,
                "context_used": len(hits) > 0,
            },
            confidence_score=confidence,
            grounded=len(hits) > 0,
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
