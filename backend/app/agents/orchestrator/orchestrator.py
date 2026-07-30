"""Coordinator that selects agents, executes tasks, and merges results."""

from __future__ import annotations

from app.agents.events.bus import AgentEvent, EventBus
from app.agents.interfaces import AgentContext, AgentResult
from app.agents.planner.planner import PlanningEngine
from app.agents.registry.registry import AgentRegistry


class Orchestrator:
    """Coordinate execution across registered agents and workflows."""

    def __init__(self, registry: AgentRegistry, event_bus: EventBus | None = None) -> None:
        self._registry = registry
        self._event_bus = event_bus or EventBus()
        self._planner = PlanningEngine()

    async def execute(self, goal: str, session_id: str | None = None) -> list[AgentResult]:
        """Create a plan, select agents, execute them, and collect results."""
        plan = self._planner.build_plan(goal)
        context = AgentContext(task_id="task-1", user_goal=goal, session_id=session_id)
        results: list[AgentResult] = []

        for step in plan.steps:
            agent_entry = self._registry.get(step.agent)
            if agent_entry is None:
                continue
            agent, _ = agent_entry
            await self._event_bus.publish(AgentEvent(event_type="agent.started", payload={"agent": step.agent}))
            await agent.initialize(context)
            result = await agent.execute(context)
            await agent.cleanup(context)
            results.append(result)
            await self._event_bus.publish(AgentEvent(event_type="agent.completed", payload={"agent": step.agent, "result": result.output}))

        return results
