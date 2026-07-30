"""Unit tests for the Sprint 4 agent runtime."""

import pytest

from app.agents.interfaces import AgentMetadata
from app.agents.planner.planner import PlanningEngine
from app.agents.registry.registry import AgentRegistry
from app.agents.runtime.runtime import AgentRuntime
from app.agents.tools.registry import ToolDefinition, ToolRegistry


def test_planning_engine_builds_steps_for_crop_issue() -> None:
    engine = PlanningEngine()
    plan = engine.build_plan("My paddy leaves are turning yellow")

    assert plan.goal
    assert any(step.agent == "knowledge_retrieval" for step in plan.steps)
    assert any(step.agent == "crop_advisory" for step in plan.steps)


def test_agent_registry_registers_and_lists_agents() -> None:
    registry = AgentRegistry()
    metadata = AgentMetadata(name="test_agent", description="test")

    class DummyAgent:
        async def initialize(self, context):
            return None

        async def execute(self, context):
            return None

        async def validate(self, result):
            return True

        async def cleanup(self, context):
            return None

        async def health(self):
            return "healthy"

        def metadata(self):
            return metadata

    registry.register(DummyAgent(), metadata)

    assert registry.get("test_agent") is not None
    assert registry.names() == ["test_agent"]


def test_tool_registry_registers_tool_definitions() -> None:
    registry = ToolRegistry()
    tool = ToolDefinition(name="calculator", description="Perform math", parameters={"expression": "string"})
    registry.register(tool)

    assert registry.get("calculator") is not None
