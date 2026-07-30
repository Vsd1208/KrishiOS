"""Coordinator that selects agents, executes tasks, and merges responses."""

from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any
from uuid import uuid4

from loguru import logger

from app.agents.contracts.events import AgentEvent, EventTypes
from app.agents.evaluation.runner import AgentEvaluator
from app.agents.events.bus import EventBus
from app.agents.execution.context import AgentStatus, ExecutionContext, ExecutionResult
from app.agents.execution.policies import DEFAULT_EXECUTION_POLICY, ExecutionTimer, run_with_timeout
from app.agents.contracts.workflow import WorkflowStepType
from app.agents.planner.planner import ExecutionPlan, PlanStep, PlanningEngine
from app.agents.registry.registry import AgentRegistry
from app.agents.security.guardrails import GuardrailEngine


class Orchestrator:
    """Coordinate execution across registered agents with sequential, parallel, and fallback support."""

    def __init__(
        self,
        registry: AgentRegistry,
        event_bus: EventBus | None = None,
        guardrail_engine: GuardrailEngine | None = None,
    ) -> None:
        self._registry = registry
        self._event_bus = event_bus or EventBus()
        self._planner = PlanningEngine()
        self._guardrails = guardrail_engine or GuardrailEngine()
        self._evaluator = AgentEvaluator()
        self._policy = DEFAULT_EXECUTION_POLICY

    async def execute(
        self,
        goal: str,
        session_id: str | None = None,
        context: ExecutionContext | None = None,
    ) -> list[ExecutionResult]:
        """Create a plan, select agents, execute them, validate, and collect results."""
        timer = ExecutionTimer()
        plan = self._planner.build_plan(goal)
        exec_context = context or ExecutionContext(session_id=session_id or str(uuid4()))

        await self._event_bus.publish(
            AgentEvent(
                event_type=EventTypes.PLAN_CREATED,
                payload={"goal": goal, "steps": [s.agent for s in plan.steps], "strategy": plan.strategy},
            )
        )

        results: list[ExecutionResult] = []
        completed_step_ids: set[str] = set()
        merged_output: dict[str, Any] = {}

        sequential_batch: list[PlanStep] = []
        parallel_batch: list[PlanStep] = []

        for step in plan.steps:
            if step.step_type == WorkflowStepType.PARALLEL:
                parallel_batch.append(step)
            else:
                if parallel_batch:
                    batch_results = await self._execute_parallel(parallel_batch, goal, exec_context, completed_step_ids)
                    results.extend(batch_results)
                    parallel_batch = []
                if sequential_batch:
                    batch_results = await self._execute_sequential(sequential_batch, goal, exec_context, completed_step_ids, merged_output)
                    results.extend(batch_results)
                    sequential_batch = []
                sequential_batch.append(step)

        if parallel_batch:
            batch_results = await self._execute_parallel(parallel_batch, goal, exec_context, completed_step_ids)
            results.extend(batch_results)
        if sequential_batch:
            batch_results = await self._execute_sequential(sequential_batch, goal, exec_context, completed_step_ids, merged_output)
            results.extend(batch_results)

        validated = await self._apply_guardrails(results, goal, exec_context)
        duration_ms = timer.elapsed_ms()

        await self._event_bus.publish(
            AgentEvent(
                event_type=EventTypes.TASK_COMPLETED,
                payload={"goal": goal, "duration_ms": duration_ms, "agent_count": len(results)},
            )
        )

        return validated

    async def _execute_sequential(
        self,
        steps: list[PlanStep],
        goal: str,
        context: ExecutionContext,
        completed: set[str],
        merged_output: dict[str, Any],
    ) -> list[ExecutionResult]:
        """Execute steps sequentially respecting dependencies."""
        results: list[ExecutionResult] = []
        for step in steps:
            if step.depends_on and not all(dep in completed for dep in step.depends_on):
                logger.warning("Orchestrator: skipping step {} — unmet dependencies {}", step.step_id, step.depends_on)
                continue
            if step.condition and not self._evaluate_condition(step.condition, merged_output):
                continue
            result = await self._execute_step(step, goal, context, merged_output)
            results.append(result)
            completed.add(step.step_id)
            if result.status == AgentStatus.FAILED and step.fallback_agent:
                fallback_step = PlanStep(
                    step_id=f"{step.step_id}_fallback",
                    agent=step.fallback_agent,
                    action=step.action,
                    parameters=step.parameters,
                )
                fallback_result = await self._execute_step(fallback_step, goal, context, merged_output)
                results.append(fallback_result)
        return results

    async def _execute_parallel(
        self,
        steps: list[PlanStep],
        goal: str,
        context: ExecutionContext,
        completed: set[str],
    ) -> list[ExecutionResult]:
        """Execute independent steps in parallel."""
        tasks = [self._execute_step(step, goal, context, {}) for step in steps]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_results: list[ExecutionResult] = []
        for step, result in zip(steps, results, strict=True):
            if isinstance(result, Exception):
                execution_results.append(
                    ExecutionResult(
                        execution_id=context.execution_id,
                        status=AgentStatus.FAILED,
                        agent_name=step.agent,
                        output={},
                        confidence_score=0.0,
                        grounded=False,
                        error_message=str(result),
                    )
                )
            else:
                execution_results.append(result)
            completed.add(step.step_id)
        return execution_results

    async def _execute_step(
        self,
        step: PlanStep,
        goal: str,
        context: ExecutionContext,
        merged_output: dict[str, Any],
    ) -> ExecutionResult:
        """Execute a single plan step with lifecycle management."""
        agent = self._registry.get(step.agent)
        if agent is None:
            logger.error("Orchestrator: agent '{}' not registered", step.agent)
            return ExecutionResult(
                execution_id=context.execution_id,
                status=AgentStatus.FAILED,
                agent_name=step.agent,
                output={},
                confidence_score=0.0,
                grounded=False,
                error_message=f"Agent '{step.agent}' not found in registry",
            )

        await self._event_bus.publish(
            AgentEvent(event_type=EventTypes.AGENT_STARTED, payload={"agent": step.agent, "action": step.action})
        )

        params = {**step.parameters, "goal": goal}

        async def _run_agent() -> ExecutionResult:
            await agent.initialize()
            try:
                result = await agent.execute(goal, context, params)
                if not await agent.validate(result):
                    result = ExecutionResult(
                        execution_id=result.execution_id,
                        status=AgentStatus.FAILED,
                        agent_name=result.agent_name,
                        output=result.output,
                        confidence_score=result.confidence_score,
                        grounded=result.grounded,
                        citations=result.citations,
                        traces=result.traces,
                        duration_ms=result.duration_ms,
                        error_message="Agent validation failed",
                    )
                return result
            finally:
                await agent.cleanup()

        try:
            result = await run_with_timeout(
                _run_agent,
                self._policy.timeout.agent_timeout_seconds,
                f"agent:{step.agent}",
            )
        except Exception as exc:
            await self._event_bus.publish(
                AgentEvent(event_type=EventTypes.AGENT_FAILED, payload={"agent": step.agent, "error": str(exc)})
            )
            return ExecutionResult(
                execution_id=context.execution_id,
                status=AgentStatus.FAILED,
                agent_name=step.agent,
                output={},
                confidence_score=0.0,
                grounded=False,
                error_message=str(exc),
            )

        merged_output[step.agent] = result.output
        await self._event_bus.publish(
            AgentEvent(
                event_type=EventTypes.AGENT_COMPLETED,
                payload={"agent": step.agent, "status": result.status.value, "confidence": result.confidence_score},
            )
        )
        return result

    async def _apply_guardrails(
        self,
        results: list[ExecutionResult],
        goal: str,
        context: ExecutionContext,
    ) -> list[ExecutionResult]:
        """Apply guardrails to the final advisory output."""
        if not results:
            return results

        primary = max(
            (r for r in results if r.status == AgentStatus.COMPLETED),
            key=lambda r: r.confidence_score,
            default=None,
        )
        if primary is None:
            return results

        output_text = self._extract_text(primary.output) or goal
        guardrail = self._guardrails.evaluate(
            output_text=output_text,
            confidence_score=primary.confidence_score,
            citations=primary.citations,
            require_citations=primary.grounded,
        )

        if not guardrail.passed:
            await self._event_bus.publish(
                AgentEvent(
                    event_type=EventTypes.GUARDRAIL_REJECTED,
                    payload={"reason": guardrail.rejection_reason, "confidence": guardrail.confidence_score},
                )
            )
            validation_agent = self._registry.get("response_validation_agent")
            if validation_agent:
                rejected = ExecutionResult(
                    execution_id=context.execution_id,
                    status=AgentStatus.COMPLETED,
                    agent_name="response_validation_agent",
                    output={
                        "passed": False,
                        "validated_text": guardrail.safe_output,
                        "rejection_reason": guardrail.rejection_reason,
                    },
                    confidence_score=guardrail.confidence_score,
                    grounded=False,
                )
                return results + [rejected]

        return results

    @staticmethod
    def _extract_text(output: dict[str, Any]) -> str:
        """Extract human-readable text from agent output."""
        for key in ("recommendation", "scheme_details", "summary", "advisory", "validated_text"):
            if key in output and output[key]:
                return str(output[key])
        return ""

    @staticmethod
    def _evaluate_condition(condition: str, merged_output: dict[str, Any]) -> bool:
        """Evaluate a simple condition against merged step outputs."""
        if condition == "has_knowledge":
            retrieval = merged_output.get("knowledge_retrieval_agent", {})
            return bool(retrieval.get("hits") or retrieval.get("total_hits"))
        return True

    def planner(self) -> PlanningEngine:
        """Return the planning engine instance."""
        return self._planner

    def event_bus(self) -> EventBus:
        """Return the orchestrator event bus."""
        return self._event_bus
