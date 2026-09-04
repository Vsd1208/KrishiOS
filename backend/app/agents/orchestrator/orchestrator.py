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
from app.agents.execution.context import (
    AgentStatus,
    ExecutionContext,
    ExecutionResult,
)
from app.agents.execution.policies import (
    DEFAULT_EXECUTION_POLICY,
    ExecutionTimer,
    run_with_timeout,
)
from app.agents.contracts.workflow import WorkflowStepType
from app.agents.planner.planner import (
    ExecutionPlan,
    PlanStep,
    PlanningEngine,
)
from app.agents.registry.registry import AgentRegistry
from app.agents.security.guardrails import GuardrailEngine


class Orchestrator:
    """Coordinate execution across registered agents.

    Supports:
    - sequential execution
    - parallel execution
    - dependency-aware execution
    - fallback agents
    - retrieval-context handoff
    - guardrail validation
    - execution tracing
    """

    def __init__(
        self,
        registry: AgentRegistry,
        event_bus: EventBus | None = None,
        guardrail_engine: GuardrailEngine | None = None,
    ) -> None:
        self._registry = registry
        self._event_bus = event_bus or EventBus()
        self._planner = PlanningEngine()
        self._guardrails = (
            guardrail_engine or GuardrailEngine()
        )
        self._evaluator = AgentEvaluator()
        self._policy = DEFAULT_EXECUTION_POLICY

    async def execute(
        self,
        goal: str,
        session_id: str | None = None,
        context: ExecutionContext | None = None,
    ) -> list[ExecutionResult]:
        """Create a plan, execute it, apply guardrails, and return results."""

        timer = ExecutionTimer()

        plan: ExecutionPlan = self._planner.build_plan(
            goal
        )

        exec_context = (
            context
            or ExecutionContext(
                session_id=session_id or str(uuid4())
            )
        )

        await self._event_bus.publish(
            AgentEvent(
                event_type=EventTypes.PLAN_CREATED,
                payload={
                    "goal": goal,
                    "steps": [
                        step.agent
                        for step in plan.steps
                    ],
                    "strategy": plan.strategy,
                },
            )
        )

        results: list[ExecutionResult] = []

        completed_step_ids: set[str] = set()

        # Stores the output of every successfully executed agent.
        #
        # Example:
        #
        # merged_output["knowledge_retrieval_agent"] = {
        #     "hits": [...],
        #     "total_hits": 5,
        #     ...
        # }
        #
        # This is later passed to dependent agents such as
        # crop_advisory_agent.
        merged_output: dict[str, Any] = {}

        sequential_batch: list[PlanStep] = []
        parallel_batch: list[PlanStep] = []

        for step in plan.steps:
            if step.step_type == WorkflowStepType.PARALLEL:
                parallel_batch.append(step)
                continue

            # Flush any pending parallel work before moving to
            # sequential execution.
            if parallel_batch:
                batch_results = await self._execute_parallel(
                    steps=parallel_batch,
                    goal=goal,
                    context=exec_context,
                    completed=completed_step_ids,
                    merged_output=merged_output,
                )

                results.extend(batch_results)
                parallel_batch = []

            # Flush any pending sequential batch.
            if sequential_batch:
                batch_results = await self._execute_sequential(
                    steps=sequential_batch,
                    goal=goal,
                    context=exec_context,
                    completed=completed_step_ids,
                    merged_output=merged_output,
                )

                results.extend(batch_results)
                sequential_batch = []

            sequential_batch.append(step)

        # Flush remaining parallel work.
        if parallel_batch:
            batch_results = await self._execute_parallel(
                steps=parallel_batch,
                goal=goal,
                context=exec_context,
                completed=completed_step_ids,
                merged_output=merged_output,
            )

            results.extend(batch_results)

        # Flush remaining sequential work.
        if sequential_batch:
            batch_results = await self._execute_sequential(
                steps=sequential_batch,
                goal=goal,
                context=exec_context,
                completed=completed_step_ids,
                merged_output=merged_output,
            )

            results.extend(batch_results)

        # Apply final guardrails.
        validated = await self._apply_guardrails(
            results=results,
            goal=goal,
            context=exec_context,
        )

        duration_ms = timer.elapsed_ms()

        await self._event_bus.publish(
            AgentEvent(
                event_type=EventTypes.TASK_COMPLETED,
                payload={
                    "goal": goal,
                    "duration_ms": duration_ms,
                    "agent_count": len(results),
                },
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
        """Execute sequential steps while respecting dependencies."""

        results: list[ExecutionResult] = []

        for step in steps:
            # --------------------------------------------------------
            # Dependency check
            # --------------------------------------------------------

            if step.depends_on:
                dependencies_met = all(
                    dependency_id in completed
                    for dependency_id in step.depends_on
                )

                if not dependencies_met:
                    logger.warning(
                        "Orchestrator: skipping step {} — "
                        "unmet dependencies {}",
                        step.step_id,
                        step.depends_on,
                    )
                    continue

            # --------------------------------------------------------
            # Conditional execution
            # --------------------------------------------------------

            if step.condition:
                condition_met = self._evaluate_condition(
                    condition=step.condition,
                    merged_output=merged_output,
                )

                if not condition_met:
                    logger.info(
                        "Orchestrator: condition '{}' "
                        "not satisfied for step {}",
                        step.condition,
                        step.step_id,
                    )
                    continue

            # --------------------------------------------------------
            # Execute step
            # --------------------------------------------------------

            result = await self._execute_step(
                step=step,
                goal=goal,
                context=context,
                merged_output=merged_output,
            )

            results.append(result)

            # Mark the planned step as completed only when execution
            # reached the agent execution stage.
            completed.add(step.step_id)

            # --------------------------------------------------------
            # Fallback agent
            # --------------------------------------------------------

            if (
                result.status == AgentStatus.FAILED
                and step.fallback_agent
            ):
                logger.warning(
                    "Orchestrator: executing fallback '{}' "
                    "for failed agent '{}'",
                    step.fallback_agent,
                    step.agent,
                )

                fallback_step = PlanStep(
                    step_id=f"{step.step_id}_fallback",
                    agent=step.fallback_agent,
                    action=step.action,
                    parameters=step.parameters,
                )

                fallback_result = await self._execute_step(
                    step=fallback_step,
                    goal=goal,
                    context=context,
                    merged_output=merged_output,
                )

                results.append(fallback_result)

                if (
                    fallback_result.status
                    == AgentStatus.COMPLETED
                ):
                    merged_output[
                        fallback_step.agent
                    ] = fallback_result.output

        return results

    async def _execute_parallel(
        self,
        steps: list[PlanStep],
        goal: str,
        context: ExecutionContext,
        completed: set[str],
        merged_output: dict[str, Any],
    ) -> list[ExecutionResult]:
        """Execute independent steps in parallel.

        Important:
        Outputs are merged into ``merged_output`` after the parallel
        batch finishes. This is required so later dependent agents can
        consume the results of parallel retrieval agents.
        """

        tasks = [
            self._execute_step(
                step=step,
                goal=goal,
                context=context,
                merged_output=merged_output,
            )
            for step in steps
        ]

        raw_results = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        execution_results: list[ExecutionResult] = []

        for step, raw_result in zip(
            steps,
            raw_results,
            strict=True,
        ):
            if isinstance(
                raw_result,
                Exception,
            ):
                logger.exception(
                    "Orchestrator: parallel agent '{}' failed: {}",
                    step.agent,
                    raw_result,
                )

                result = ExecutionResult(
                    execution_id=context.execution_id,
                    status=AgentStatus.FAILED,
                    agent_name=step.agent,
                    output={},
                    confidence_score=0.0,
                    grounded=False,
                    error_message=str(raw_result),
                )
            else:
                result = raw_result

            execution_results.append(result)

            # --------------------------------------------------------
            # CRITICAL FIX:
            #
            # Store successful agent outputs in merged_output.
            #
            # This makes:
            #
            # knowledge_retrieval_agent
            #          ↓
            # merged_output
            #          ↓
            # crop_advisory_agent
            #
            # actually work when retrieval executes in parallel.
            # --------------------------------------------------------

            if result.status == AgentStatus.COMPLETED:
                merged_output[
                    step.agent
                ] = result.output

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

        agent = self._registry.get(
            step.agent
        )

        if agent is None:
            logger.error(
                "Orchestrator: agent '{}' not registered",
                step.agent,
            )

            return ExecutionResult(
                execution_id=context.execution_id,
                status=AgentStatus.FAILED,
                agent_name=step.agent,
                output={},
                confidence_score=0.0,
                grounded=False,
                error_message=(
                    f"Agent '{step.agent}' "
                    "not found in registry"
                ),
            )

        await self._event_bus.publish(
            AgentEvent(
                event_type=EventTypes.AGENT_STARTED,
                payload={
                    "agent": step.agent,
                    "action": step.action,
                },
            )
        )

        # ------------------------------------------------------------
        # Base parameters
        # ------------------------------------------------------------

        params: dict[str, Any] = {
            **step.parameters,
            "goal": goal,
        }

        # ------------------------------------------------------------
        # Retrieval → Advisory handoff
        # ------------------------------------------------------------
        #
        # The knowledge retrieval agent may have executed in a
        # parallel batch. Because _execute_parallel now writes its
        # result into merged_output, the advisory agent can consume
        # that exact verified retrieval result.
        #
        # IMPORTANT:
        # merged_output stores result.output, not the entire
        # ExecutionResult.
        # ------------------------------------------------------------

        if step.agent == "crop_advisory_agent":
            retrieval_output = merged_output.get(
                "knowledge_retrieval_agent"
            )

            if isinstance(
                retrieval_output,
                dict,
            ):
                params[
                    "retrieval_context"
                ] = retrieval_output

                logger.debug(
                    "Orchestrator: passing {} retrieval hits "
                    "to crop_advisory_agent",
                    self._count_retrieval_hits(
                        retrieval_output
                    ),
                )

        async def _run_agent() -> ExecutionResult:
            await agent.initialize()

            try:
                result = await agent.execute(
                    goal,
                    context,
                    params,
                )

                # ----------------------------------------------------
                # Agent-level validation
                # ----------------------------------------------------

                if not await agent.validate(
                    result
                ):
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
                        error_message=(
                            "Agent validation failed"
                        ),
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
            logger.exception(
                "Orchestrator: agent '{}' failed",
                step.agent,
            )

            await self._event_bus.publish(
                AgentEvent(
                    event_type=EventTypes.AGENT_FAILED,
                    payload={
                        "agent": step.agent,
                        "error": str(exc),
                    },
                )
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

        # ------------------------------------------------------------
        # Merge successful output
        # ------------------------------------------------------------

        if result.status == AgentStatus.COMPLETED:
            merged_output[
                step.agent
            ] = result.output

        await self._event_bus.publish(
            AgentEvent(
                event_type=EventTypes.AGENT_COMPLETED,
                payload={
                    "agent": step.agent,
                    "status": result.status.value,
                    "confidence": result.confidence_score,
                },
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

        completed_results = [
            result
            for result in results
            if result.status
            == AgentStatus.COMPLETED
        ]

        if not completed_results:
            return results

        # Select the strongest completed response.
        primary = max(
            completed_results,
            key=lambda result: result.confidence_score,
            default=None,
        )

        if primary is None:
            return results

        output_text = (
            self._extract_text(
                primary.output
            )
            or goal
        )

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
                    payload={
                        "reason": guardrail.rejection_reason,
                        "confidence": guardrail.confidence_score,
                    },
                )
            )

            validation_agent = self._registry.get(
                "response_validation_agent"
            )

            if validation_agent:
                rejected = ExecutionResult(
                    execution_id=context.execution_id,
                    status=AgentStatus.COMPLETED,
                    agent_name="response_validation_agent",
                    output={
                        "passed": False,
                        "validated_text": guardrail.safe_output,
                        "rejection_reason": (
                            guardrail.rejection_reason
                        ),
                    },
                    confidence_score=guardrail.confidence_score,
                    grounded=False,
                )

                return results + [rejected]

        return results

    @staticmethod
    def _extract_text(
        output: dict[str, Any],
    ) -> str:
        """Extract human-readable text from agent output."""

        text_keys = (
            "recommendation",
            "scheme_details",
            "summary",
            "advisory",
            "validated_text",
        )

        for key in text_keys:
            value = output.get(
                key
            )

            if value:
                return str(value)

        return ""

    @staticmethod
    def _evaluate_condition(
        condition: str,
        merged_output: dict[str, Any],
    ) -> bool:
        """Evaluate a simple condition against merged outputs."""

        if condition == "has_knowledge":
            retrieval = merged_output.get(
                "knowledge_retrieval_agent",
                {},
            )

            if not isinstance(
                retrieval,
                dict,
            ):
                return False

            hits = retrieval.get(
                "hits",
                [],
            )

            total_hits = retrieval.get(
                "total_hits",
                0,
            )

            return bool(
                isinstance(hits, list)
                and len(hits) > 0
            ) or bool(total_hits)

        return True

    @staticmethod
    def _count_retrieval_hits(
        retrieval_output: dict[str, Any],
    ) -> int:
        """Safely count retrieval hits for logging."""

        hits = retrieval_output.get(
            "hits",
            [],
        )

        if isinstance(
            hits,
            list,
        ):
            return len(hits)

        return 0

    def planner(self) -> PlanningEngine:
        """Return the planning engine instance."""

        return self._planner

    def event_bus(self) -> EventBus:
        """Return the orchestrator event bus instance."""

        return self._event_bus