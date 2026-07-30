"""Weather Intelligence Agent interface for climate advisories and rainfall warnings."""

from time import perf_counter
from typing import Any

from loguru import logger

from app.agents.base import AgentMetadata, BaseAgent
from app.agents.execution.context import AgentStatus, AgentStepTrace, ExecutionContext, ExecutionResult
from app.agents.tools.stubs import WeatherApiTool


class WeatherIntelligenceAgent(BaseAgent):
    """Production Weather Intelligence Agent interface for KrishiOS."""

    def __init__(self, weather_tool: WeatherApiTool) -> None:
        metadata = AgentMetadata(
            name="weather_intelligence_agent",
            description="Provides real-time weather warnings, monsoon forecasts, and irrigation alerts.",
            capabilities=["weather", "climate", "rainfall", "irrigation_alert"],
            input_schema={"state": "string", "district": "string"},
            output_schema={"forecast": "string", "advisory": "string"},
            supported_tools=["weather_api"],
            priority=15,
            version="1.0.0",
        )
        super().__init__(metadata)
        self._weather_tool = weather_tool

    async def initialize(self) -> None:
        self._status = AgentStatus.IDLE
        logger.info("WeatherIntelligenceAgent: initialized")

    async def execute(
        self,
        task: str,
        context: ExecutionContext,
        parameters: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        t0 = perf_counter()
        self._status = AgentStatus.RUNNING

        res = await self._weather_tool.execute({
            "state": context.state or "Punjab",
            "district": context.district or "Ludhiana",
        })

        duration_ms = (perf_counter() - t0) * 1000
        trace = AgentStepTrace(
            step_number=len(context.traces) + 1,
            agent_name=self.metadata.name,
            action="fetch_weather_forecast",
            input_data={"district": context.district},
            output_data=res.data,
            duration_ms=duration_ms,
        )
        context.add_trace(trace)

        self._status = AgentStatus.COMPLETED
        return ExecutionResult(
            execution_id=context.execution_id,
            status=AgentStatus.COMPLETED,
            agent_name=self.metadata.name,
            output=res.data,
            confidence_score=0.9,
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
