"""Workflow engine supporting sequential, parallel, conditional, loop, retry, and timeout steps."""

from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

from loguru import logger

from app.agents.contracts.events import AgentEvent, EventTypes
from app.agents.contracts.workflow import (
    WorkflowDefinition,
    WorkflowExecutionResult,
    WorkflowStep,
    WorkflowStepType,
)
from app.agents.events.bus import EventBus
from app.agents.execution.context import AgentStatus, ExecutionContext, ExecutionResult
from app.agents.execution.policies import DEFAULT_EXECUTION_POLICY, run_with_timeout
from app.agents.registry.registry import AgentRegistry
from app.agents.workflows.definitions import BUILTIN_WORKFLOWS


class WorkflowEngine:
    """Execute reusable workflow definitions with full step-type support."""

    def __init__(self, registry: AgentRegistry, event_bus: EventBus | None = None) -> None:
        self._registry = registry
        self._event_bus = event_bus or EventBus()
        self._workflows: dict[str, WorkflowDefinition] = dict(BUILTIN_WORKFLOWS)
        self._policy = DEFAULT_EXECUTION_POLICY
        self._pending_approvals: dict[str, bool] = {}

    def register(self, workflow: WorkflowDefinition) -> None:
        """Register a reusable workflow definition."""
        self._workflows[workflow.workflow_id] = workflow
        logger.info("WorkflowEngine: registered workflow '{}'", workflow.workflow_id)

    def get(self, workflow_id: str) -> WorkflowDefinition | None:
        """Return a workflow definition by identifier."""
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> list[WorkflowDefinition]:
        """Return all registered workflow definitions."""
        return list(self._workflows.values())

    async def run(
        self,
        workflow_id: str,
        goal: str,
        context: ExecutionContext | None = None,
        parameters: dict[str, Any] | None = None,
        approved_steps: set[str] | None = None,
    ) -> WorkflowExecutionResult:
        """Execute a workflow by identifier."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            return WorkflowExecutionResult(
                workflow_id=workflow_id,
                status="failed",
                error_message=f"Workflow '{workflow_id}' not found",
            )

        started = perf_counter()
        exec_context = context or ExecutionContext()
        params = parameters or {}
        approvals = approved_steps or set()

        await self._event_bus.publish(
            AgentEvent(
                event_type=EventTypes.WORKFLOW_STARTED,
                payload={"workflow_id": workflow_id, "goal": goal},
            )
        )

        step_results: list[dict[str, Any]] = []
        merged_output: dict[str, Any] = {}
        completed_steps: set[str] = set()

        for step in workflow.steps:
            if step.depends_on and not all(dep in completed_steps for dep in step.depends_on):
                step_results.append({
                    "step_id": step.step_id,
                    "status": "skipped",
                    "reason": "unmet_dependencies",
                })
                continue

            if step.requires_approval and step.step_id not in approvals:
                step_results.append({
                    "step_id": step.step_id,
                    "status": "pending_approval",
                })
                continue

            result = await self._execute_workflow_step(step, goal, exec_context, params, merged_output)
            step_results.append({
                "step_id": step.step_id,
                "agent": step.agent_name,
                "status": result.status.value,
                "output": result.output,
                "confidence": result.confidence_score,
                "error": result.error_message,
            })
            merged_output[step.step_id] = result.output
            completed_steps.add(step.step_id)

            if result.status == AgentStatus.FAILED and step.fallback_agent:
                fallback = WorkflowStep(
                    step_id=f"{step.step_id}_fallback",
                    agent_name=step.fallback_agent,
                    action=step.action,
                    parameters=step.parameters,
                )
                fallback_result = await self._execute_workflow_step(fallback, goal, exec_context, params, merged_output)
                step_results.append({
                    "step_id": fallback.step_id,
                    "agent": fallback.agent_name,
                    "status": fallback_result.status.value,
                    "output": fallback_result.output,
                    "fallback": True,
                })

        duration_ms = (perf_counter() - started) * 1000
        status = "completed" if all(r.get("status") != "failed" for r in step_results) else "partial"

        await self._event_bus.publish(
            AgentEvent(
                event_type=EventTypes.WORKFLOW_COMPLETED,
                payload={"workflow_id": workflow_id, "status": status, "duration_ms": duration_ms},
            )
        )

        return WorkflowExecutionResult(
            workflow_id=workflow_id,
            status=status,
            step_results=step_results,
            merged_output=merged_output,
            duration_ms=duration_ms,
        )

    async def _execute_workflow_step(
        self,
        step: WorkflowStep,
        goal: str,
        context: ExecutionContext,
        global_params: dict[str, Any],
        merged_output: dict[str, Any],
    ) -> ExecutionResult:
        """Execute a single workflow step according to its step type."""
        if step.step_type == WorkflowStepType.CONDITIONAL and step.condition:
            if not self._evaluate_condition(step.condition, merged_output):
                return ExecutionResult(
                    execution_id=context.execution_id,
                    status=AgentStatus.COMPLETED,
                    agent_name=step.agent_name,
                    output={"skipped": True, "condition": step.condition},
                    confidence_score=1.0,
                    grounded=True,
                )

        if step.step_type == WorkflowStepType.LOOP:
            return await self._execute_loop(step, goal, context, global_params)

        return await self._invoke_agent(step, goal, context, global_params)

    async def _execute_loop(
        self,
        step: WorkflowStep,
        goal: str,
        context: ExecutionContext,
        global_params: dict[str, Any],
    ) -> ExecutionResult:
        """Execute a loop step up to max_iterations."""
        last_result: ExecutionResult | None = None
        for iteration in range(step.max_iterations):
            result = await self._invoke_agent(step, goal, context, {**global_params, "iteration": iteration})
            last_result = result
            if result.status == AgentStatus.COMPLETED:
                break
        return last_result or ExecutionResult(
            execution_id=context.execution_id,
            status=AgentStatus.FAILED,
            agent_name=step.agent_name,
            output={},
            confidence_score=0.0,
            grounded=False,
            error_message="Loop produced no results",
        )

    async def _invoke_agent(
        self,
        step: WorkflowStep,
        goal: str,
        context: ExecutionContext,
        global_params: dict[str, Any],
    ) -> ExecutionResult:
        """Invoke an agent for a workflow step with retry and timeout."""
        agent = self._registry.get(step.agent_name)
        if agent is None:
            return ExecutionResult(
                execution_id=context.execution_id,
                status=AgentStatus.FAILED,
                agent_name=step.agent_name,
                output={},
                confidence_score=0.0,
                grounded=False,
                error_message=f"Agent '{step.agent_name}' not registered",
            )

        step_params = {**global_params, **step.parameters, "goal": goal}
        timeout = step.timeout_seconds or self._policy.timeout.agent_timeout_seconds
        retries = 0
        max_retries = 2 if step.step_type == WorkflowStepType.RETRY else 0

        while retries <= max_retries:
            try:
                async def _run() -> ExecutionResult:
                    await agent.initialize()
                    try:
                        return await agent.execute(goal, context, step_params)
                    finally:
                        await agent.cleanup()

                return await run_with_timeout(_run, timeout, f"workflow:{step.step_id}")
            except Exception as exc:
                retries += 1
                if retries > max_retries:
                    return ExecutionResult(
                        execution_id=context.execution_id,
                        status=AgentStatus.FAILED,
                        agent_name=step.agent_name,
                        output={},
                        confidence_score=0.0,
                        grounded=False,
                        error_message=str(exc),
                    )

        return ExecutionResult(
            execution_id=context.execution_id,
            status=AgentStatus.FAILED,
            agent_name=step.agent_name,
            output={},
            confidence_score=0.0,
            grounded=False,
            error_message="Unexpected workflow execution failure",
        )

    @staticmethod
    def _evaluate_condition(condition: str, merged_output: dict[str, Any]) -> bool:
        """Evaluate workflow step conditions."""
        if condition == "has_results":
            return bool(merged_output)
        return True
