"""Agent Runtime Engine — lifecycle, registration, execution, and observability."""

from __future__ import annotations

from time import perf_counter
from typing import Any
from uuid import uuid4

from loguru import logger

from app.agents.communication.bus import CommunicationBus
from app.agents.contracts.events import AgentEvent, EventTypes
from app.agents.contracts.workflow import WorkflowExecutionResult
from app.agents.evaluation.runner import AgentEvaluator
from app.agents.events.bus import EventBus
from app.agents.execution.context import ExecutionContext, ExecutionResult
from app.agents.execution.policies import DEFAULT_EXECUTION_POLICY, ExecutionPolicy, ExecutionTimer
from app.agents.memory.provider import InMemoryProvider, MemoryProvider
from app.agents.monitoring.collector import RuntimeMetricsCollector
from app.agents.orchestrator.orchestrator import Orchestrator
from app.agents.planner.planner import ExecutionPlan
from app.agents.prompts.registry import PromptRegistry
from app.agents.registry.registry import AgentRegistry
from app.agents.tools.registry import ToolRegistry
from app.agents.workflows.engine import WorkflowEngine


class AgentRuntimeEngine:
    """Top-level runtime engine for agent lifecycle, planning, execution, and monitoring."""

    def __init__(
        self,
        registry: AgentRegistry,
        tool_registry: ToolRegistry,
        event_bus: EventBus | None = None,
        memory_provider: MemoryProvider | None = None,
        policy: ExecutionPolicy | None = None,
    ) -> None:
        self._registry = registry
        self._tool_registry = tool_registry
        self._event_bus = event_bus or EventBus()
        self._memory = memory_provider or InMemoryProvider()
        self._policy = policy or DEFAULT_EXECUTION_POLICY
        self._orchestrator = Orchestrator(registry, self._event_bus)
        self._workflow_engine = WorkflowEngine(registry, self._event_bus)
        self._communication = CommunicationBus()
        self._prompts = PromptRegistry()
        self._metrics = RuntimeMetricsCollector()
        self._evaluator = AgentEvaluator()
        self._started_at = perf_counter()

    async def execute(
        self,
        goal: str,
        session_id: str | None = None,
        context: ExecutionContext | None = None,
    ) -> list[ExecutionResult]:
        """Execute a user goal through planning, orchestration, and validation."""
        timer = ExecutionTimer()
        exec_context = context or ExecutionContext(session_id=session_id or str(uuid4()))

        session_memory = await self._memory.get_session(exec_context.session_id)
        session_memory.set("last_goal", goal)

        plan_timer = ExecutionTimer()
        plan = self._orchestrator.planner().build_plan(goal)
        self._metrics.record("planning_time_ms", plan_timer.elapsed_ms())

        results = await self._orchestrator.execute(goal, exec_context.session_id, exec_context)

        for result in results:
            self._metrics.record("execution_time_ms", result.duration_ms)
            self._metrics.record("agent_confidence", result.confidence_score)
            if result.status.value == "failed":
                self._metrics.record_failure(result.agent_name)

        self._metrics.record("total_execution_time_ms", timer.elapsed_ms())
        self._metrics.record_agent_utilization([r.agent_name for r in results])

        return results

    async def run_workflow(
        self,
        workflow_id: str,
        goal: str,
        session_id: str | None = None,
        parameters: dict[str, Any] | None = None,
        approved_steps: set[str] | None = None,
    ) -> WorkflowExecutionResult:
        """Execute a registered workflow definition."""
        timer = ExecutionTimer()
        context = ExecutionContext(session_id=session_id or str(uuid4()))
        result = await self._workflow_engine.run(workflow_id, goal, context, parameters, approved_steps)
        self._metrics.record("workflow_duration_ms", timer.elapsed_ms())
        return result

    def register_agent(self, agent: Any) -> None:
        """Register an agent with the runtime."""
        self._registry.register(agent)

    def register_tool(self, tool: Any) -> None:
        """Register a tool with the runtime."""
        self._tool_registry.register(tool)

    async def invoke_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        agent_name: str,
    ):
        """Invoke a tool through the tool registry with metrics tracking."""
        timer = ExecutionTimer()
        result = await self._tool_registry.invoke(tool_name, parameters, agent_name)
        self._metrics.record("tool_latency_ms", timer.elapsed_ms())
        if not result.success:
            await self._event_bus.publish(
                AgentEvent(
                    event_type=EventTypes.TOOL_FAILED,
                    payload={"tool": tool_name, "agent": agent_name, "error": result.error_message},
                )
            )
        return result

    def get_plan(self, goal: str) -> ExecutionPlan:
        """Return the execution plan for a goal without running it."""
        return self._orchestrator.planner().build_plan(goal)

    async def health_check(self) -> dict[str, Any]:
        """Return runtime health including all registered agents."""
        agent_health = await self._registry.health_check_all()
        unhealthy = [name for name, h in agent_health.items() if h.get("status") != "healthy"]
        return {
            "status": "healthy" if not unhealthy else "degraded",
            "uptime_seconds": perf_counter() - self._started_at,
            "registered_agents": self._registry.count(),
            "registered_tools": self._tool_registry.count(),
            "unhealthy_agents": unhealthy,
            "agents": agent_health,
            "metrics": self._metrics.summarize(),
        }

    def registry(self) -> AgentRegistry:
        """Return the agent registry."""
        return self._registry

    def tools(self) -> ToolRegistry:
        """Return the tool registry."""
        return self._tool_registry

    def events(self) -> EventBus:
        """Return the event bus."""
        return self._event_bus

    def workflows(self) -> WorkflowEngine:
        """Return the workflow engine."""
        return self._workflow_engine

    def metrics(self) -> RuntimeMetricsCollector:
        """Return the metrics collector."""
        return self._metrics

    def prompts(self) -> PromptRegistry:
        """Return the prompt registry."""
        return self._prompts

    def communication(self) -> CommunicationBus:
        """Return the inter-agent communication bus."""
        return self._communication

    def evaluate_results(self, results: list[ExecutionResult]) -> dict[str, Any]:
        """Evaluate a batch of execution results."""
        return self._evaluator.evaluate_batch(results)
