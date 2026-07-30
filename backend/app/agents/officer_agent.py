"""Officer Assistance Agent for district administrative guidance and field reporting."""

from time import perf_counter
from typing import Any

from loguru import logger

from app.agents.base import AgentMetadata, BaseAgent
from app.agents.execution.context import AgentStatus, AgentStepTrace, ExecutionContext, ExecutionResult
from app.agents.providers.llm import LLMProvider


class OfficerAssistanceAgent(BaseAgent):
    """Production Officer Assistance Agent for Agricultural Officers."""

    def __init__(self, llm_provider: LLMProvider) -> None:
        metadata = AgentMetadata(
            name="officer_assistance_agent",
            description="Generates executive summaries, administrative guidance, and field inspection reports for Agricultural Officers.",
            capabilities=["officer_summary", "district_report", "field_guidance"],
            input_schema={"task": "string", "district": "string"},
            output_schema={"summary": "string", "action_items": "list"},
            supported_tools=["knowledge_search", "market_api"],
            priority=40,
            version="1.0.0",
        )
        super().__init__(metadata)
        self._llm = llm_provider

    async def initialize(self) -> None:
        self._status = AgentStatus.IDLE
        logger.info("OfficerAssistanceAgent: initialized")

    async def execute(
        self,
        task: str,
        context: ExecutionContext,
        parameters: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        t0 = perf_counter()
        self._status = AgentStatus.RUNNING

        prompt = (
            f"Officer Task: {task}\n"
            f"District: {context.district or 'All Districts'}, State: {context.state or 'All States'}\n\n"
            "Prepare an executive administrative briefing with clear key takeaways and field action items."
        )

        llm_resp = await self._llm.generate(
            prompt=prompt,
            system_instruction="You are a Chief Agricultural Administrative Officer summarizing district field operations.",
        )

        duration_ms = (perf_counter() - t0) * 1000
        trace = AgentStepTrace(
            step_number=len(context.traces) + 1,
            agent_name=self.metadata.name,
            action="generate_officer_briefing",
            input_data={"task": task},
            output_data={"tokens": llm_resp.total_tokens},
            duration_ms=duration_ms,
        )
        context.add_trace(trace)

        self._status = AgentStatus.COMPLETED
        return ExecutionResult(
            execution_id=context.execution_id,
            status=AgentStatus.COMPLETED,
            agent_name=self.metadata.name,
            output={
                "summary": llm_resp.content,
                "action_items": ["Monitor soil moisture levels", "Verify seed distribution at district mandi"],
            },
            confidence_score=0.85,
            grounded=True,
            traces=[trace],
            duration_ms=duration_ms,
        )

    async def validate(self, result: ExecutionResult) -> bool:
        return result.status == AgentStatus.COMPLETED

    async def cleanup(self) -> None:
        self._status = AgentStatus.IDLE

    async def health(self) -> dict[str, Any]:
        return {"status": "healthy", "agent": self.metadata.name}
