"""Comprehensive unit tests for the Sprint 4 enterprise agent runtime."""

from __future__ import annotations

import pytest

from app.agents.contracts.agent import AgentMetadata, BaseAgent
from app.agents.contracts.tool import ToolMetadata
from app.agents.evaluation.runner import AgentEvaluator
from app.agents.events.bus import EventBus
from app.agents.execution.context import AgentStatus, ExecutionContext, ExecutionResult
from app.agents.memory.provider import InMemoryProvider
from app.agents.planner.planner import PlanningEngine
from app.agents.prompts.registry import PromptRegistry
from app.agents.registry.registry import AgentRegistry
from app.agents.tools.registry import ToolRegistry
from app.agents.workflows.definitions import BUILTIN_WORKFLOWS
from app.agents.workflows.engine import WorkflowEngine


def test_planning_engine_builds_steps_for_crop_issue() -> None:
    engine = PlanningEngine()
    plan = engine.build_plan("My paddy leaves are turning yellow")

    assert plan.goal
    assert any(step.agent == "knowledge_retrieval_agent" for step in plan.steps)
    assert any(step.agent == "crop_advisory_agent" for step in plan.steps)
    assert any(step.agent == "response_validation_agent" for step in plan.steps)


def test_planning_engine_detects_weather_queries() -> None:
    engine = PlanningEngine()
    plan = engine.build_plan("What is the rainfall forecast for Ludhiana this week?")

    assert any(step.agent == "weather_intelligence_agent" for step in plan.steps)


def test_planning_engine_detects_scheme_queries() -> None:
    engine = PlanningEngine()
    plan = engine.build_plan("Am I eligible for PM-KISAN subsidy?")

    assert any(step.agent == "govt_scheme_agent" for step in plan.steps)


def test_agent_registry_registers_and_lists_agents() -> None:
    registry = AgentRegistry()

    class DummyAgent(BaseAgent):
        def __init__(self) -> None:
            super().__init__(
                AgentMetadata(
                    name="test_agent",
                    description="test",
                    capabilities=["test"],
                    input_schema={"query": "string"},
                    output_schema={"result": "string"},
                    supported_tools=[],
                )
            )

        async def initialize(self) -> None:
            pass

        async def execute(self, task: str, context: ExecutionContext, parameters=None) -> ExecutionResult:
            return ExecutionResult(
                execution_id=context.execution_id,
                status=AgentStatus.COMPLETED,
                agent_name="test_agent",
                output={"result": task},
                confidence_score=0.9,
                grounded=True,
            )

        async def validate(self, result: ExecutionResult) -> bool:
            return True

        async def cleanup(self) -> None:
            pass

        async def health(self) -> dict[str, object]:
            return {"status": "healthy"}

    registry.register(DummyAgent())

    assert registry.get("test_agent") is not None
    assert registry.names() == ["test_agent"]


def test_agent_registry_discovers_by_capability() -> None:
    registry = AgentRegistry()

    class CapAgent(BaseAgent):
        def __init__(self, name: str, caps: list[str]) -> None:
            super().__init__(
                AgentMetadata(
                    name=name,
                    description="cap test",
                    capabilities=caps,
                    input_schema={},
                    output_schema={},
                    supported_tools=[],
                )
            )

        async def initialize(self) -> None:
            pass

        async def execute(self, task: str, context: ExecutionContext, parameters=None) -> ExecutionResult:
            return ExecutionResult(
                execution_id=context.execution_id,
                status=AgentStatus.COMPLETED,
                agent_name=self.metadata.name,
                output={},
                confidence_score=1.0,
                grounded=True,
            )

        async def validate(self, result: ExecutionResult) -> bool:
            return True

        async def cleanup(self) -> None:
            pass

        async def health(self) -> dict[str, object]:
            return {"status": "healthy"}

    registry.register(CapAgent("agent_a", ["weather"]))
    registry.register(CapAgent("agent_b", ["retrieval"]))

    assert len(registry.discover_by_capability("weather")) == 1


def test_tool_registry_registers_tool_definitions() -> None:
    from app.agents.contracts.tool import BaseTool, ToolResult

    class StubTool(BaseTool):
        def __init__(self) -> None:
            super().__init__(
                ToolMetadata(
                    name="calculator",
                    description="Perform math",
                    parameters={"expression": "string"},
                )
            )

        async def execute(self, parameters: dict) -> ToolResult:
            return ToolResult(tool_name="calculator", success=True, data={"result": 4})

    registry = ToolRegistry()
    registry.register(StubTool())

    assert registry.get("calculator") is not None
    assert registry.count() == 1


@pytest.mark.asyncio
async def test_tool_registry_invoke() -> None:
    from app.agents.contracts.tool import BaseTool, ToolResult

    class AddTool(BaseTool):
        def __init__(self) -> None:
            super().__init__(
                ToolMetadata(name="adder", description="add", parameters={})
            )

        async def execute(self, parameters: dict) -> ToolResult:
            return ToolResult(
                tool_name="adder",
                success=True,
                data={"sum": parameters.get("a", 0) + parameters.get("b", 0)},
            )

    registry = ToolRegistry()
    registry.register(AddTool())
    result = await registry.invoke("adder", {"a": 2, "b": 3}, "test_agent")
    assert result.success
    assert result.data["sum"] == 5


def test_event_bus_publish_and_history() -> None:
    bus = EventBus()
    events_received: list[str] = []

    async def handler(event) -> None:
        events_received.append(event.event_type)

    import asyncio

    bus.subscribe("test.event", handler)

    async def _run() -> None:
        from app.agents.contracts.events import AgentEvent
        await bus.publish(AgentEvent(event_type="test.event", payload={"key": "value"}))

    asyncio.get_event_loop().run_until_complete(_run())
    assert "test.event" in [e.event_type for e in bus.history()]


def test_prompt_registry_default_templates() -> None:
    registry = PromptRegistry()
    templates = registry.list_templates()
    assert len(templates) >= 3
    template = registry.get("crop_advisory")
    assert template is not None
    prompt, system = template.render(
        query="yellow leaves",
        crop="paddy",
        region="Punjab",
        season="kharif",
        context="test context",
    )
    assert "yellow leaves" in prompt
    assert system is not None


def test_memory_provider_session_scoping() -> None:
    import asyncio

    provider = InMemoryProvider()

    async def _run() -> None:
        session = await provider.get_session("session-1")
        session.set("key", "value")
        assert session.get("key") == "value"
        await provider.clear_session("session-1")

    asyncio.get_event_loop().run_until_complete(_run())


def test_evaluator_scores_results() -> None:
    evaluator = AgentEvaluator()
    result = ExecutionResult(
        execution_id=ExecutionContext().execution_id,
        status=AgentStatus.COMPLETED,
        agent_name="test",
        output={"text": "advice"},
        confidence_score=0.8,
        grounded=True,
        citations=[{"source": "ICAR"}],
    )
    report = evaluator.evaluate(result)
    assert report.passed
    assert report.overall_score > 0.5


def test_builtin_workflows_registered() -> None:
    assert "crop_diagnosis" in BUILTIN_WORKFLOWS
    assert "scheme_lookup" in BUILTIN_WORKFLOWS
    assert "officer_briefing" in BUILTIN_WORKFLOWS


@pytest.mark.asyncio
async def test_workflow_engine_lists_workflows() -> None:
    registry = AgentRegistry()
    engine = WorkflowEngine(registry)
    workflows = engine.list_workflows()
    assert len(workflows) >= 3


@pytest.mark.asyncio
async def test_runtime_engine_health_check() -> None:
    from app.agents.runtime.factory import build_runtime_engine

    runtime = build_runtime_engine()
    health = await runtime.health_check()
    assert health["registered_agents"] == 6
    assert health["registered_tools"] >= 7
    assert health["status"] in ("healthy", "degraded")


def test_api_list_agents(client) -> None:
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    agents = response.json()
    assert len(agents) == 6
    names = {a["name"] for a in agents}
    assert "knowledge_retrieval_agent" in names
    assert "crop_advisory_agent" in names


def test_api_runtime_status(client) -> None:
    response = client.get("/api/v1/runtime/status")
    assert response.status_code == 200
    data = response.json()
    assert data["registered_agents"] == 6
    assert "metrics" in data


def test_api_get_agent_by_id(client) -> None:
    response = client.get("/api/v1/agents/knowledge_retrieval_agent")
    assert response.status_code == 200
    assert response.json()["name"] == "knowledge_retrieval_agent"


def test_api_get_agent_not_found(client) -> None:
    response = client.get("/api/v1/agents/nonexistent_agent")
    assert response.status_code == 404


def test_api_workflow_not_found(client) -> None:
    response = client.post(
        "/api/v1/workflows/run",
        json={"workflow_id": "nonexistent", "goal": "test goal query"},
    )
    assert response.status_code == 404
