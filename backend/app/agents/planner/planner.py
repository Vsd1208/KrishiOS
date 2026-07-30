"""Structured planning engine for agent workflow generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.contracts.workflow import WorkflowStepType


@dataclass(slots=True)
class PlanStep:
    """A single step in an execution plan."""

    step_id: str
    agent: str
    action: str
    step_type: WorkflowStepType = WorkflowStepType.SEQUENTIAL
    depends_on: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    condition: str | None = None
    fallback_agent: str | None = None


@dataclass(slots=True)
class ExecutionPlan:
    """Structured execution plan for a user-given goal."""

    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    strategy: str = "sequential"


class PlanningEngine:
    """Generate structured execution plans for agricultural reasoning tasks."""

    _CROP_KEYWORDS = ("yellow", "disease", "paddy", "wheat", "crop", "pest", "blight", "rust", "leaf")
    _WEATHER_KEYWORDS = ("weather", "rain", "rainfall", "monsoon", "irrigation", "drought", "forecast")
    _SCHEME_KEYWORDS = ("scheme", "subsid", "government", "pm-kisan", "pm kisan", "insurance", "pmfby")
    _OFFICER_KEYWORDS = ("officer", "district", "report", "administrative", "field inspection")

    def build_plan(self, user_goal: str) -> ExecutionPlan:
        """Create a structured plan based on the user goal."""
        goal_lower = user_goal.casefold()
        steps: list[PlanStep] = []
        step_counter = 0

        def _next_id(prefix: str) -> str:
            nonlocal step_counter
            step_counter += 1
            return f"{prefix}_{step_counter}"

        needs_knowledge = any(kw in goal_lower for kw in self._CROP_KEYWORDS)
        needs_weather = any(kw in goal_lower for kw in self._WEATHER_KEYWORDS)
        needs_scheme = any(kw in goal_lower for kw in self._SCHEME_KEYWORDS)
        needs_officer = any(kw in goal_lower for kw in self._OFFICER_KEYWORDS)

        parallel_steps: list[PlanStep] = []

        if needs_weather:
            parallel_steps.append(
                PlanStep(
                    step_id=_next_id("weather"),
                    agent="weather_intelligence_agent",
                    action="inspect_weather",
                    step_type=WorkflowStepType.PARALLEL,
                    parameters={"goal": user_goal},
                )
            )

        if needs_scheme:
            parallel_steps.append(
                PlanStep(
                    step_id=_next_id("scheme"),
                    agent="govt_scheme_agent",
                    action="search_scheme_documents",
                    step_type=WorkflowStepType.PARALLEL,
                    parameters={"goal": user_goal},
                )
            )

        if needs_knowledge or (not needs_weather and not needs_scheme and not needs_officer):
            retrieval_id = _next_id("retrieval")
            parallel_steps.append(
                PlanStep(
                    step_id=retrieval_id,
                    agent="knowledge_retrieval_agent",
                    action="search_knowledge",
                    step_type=WorkflowStepType.PARALLEL,
                    parameters={"goal": user_goal, "query": user_goal},
                )
            )
            steps.extend(parallel_steps)
            steps.append(
                PlanStep(
                    step_id=_next_id("advisory"),
                    agent="crop_advisory_agent",
                    action="generate_advice",
                    step_type=WorkflowStepType.SEQUENTIAL,
                    depends_on=[retrieval_id],
                    parameters={"goal": user_goal, "query": user_goal},
                )
            )
        else:
            steps.extend(parallel_steps)

        if needs_officer:
            steps.append(
                PlanStep(
                    step_id=_next_id("officer"),
                    agent="officer_assistance_agent",
                    action="generate_summary",
                    step_type=WorkflowStepType.SEQUENTIAL,
                    parameters={"goal": user_goal, "task": user_goal},
                )
            )

        steps.append(
            PlanStep(
                step_id=_next_id("validation"),
                agent="response_validation_agent",
                action="validate_response",
                step_type=WorkflowStepType.SEQUENTIAL,
                parameters={"goal": user_goal, "require_citations": needs_knowledge},
            )
        )

        strategy = "parallel" if len(parallel_steps) > 1 else "sequential"
        return ExecutionPlan(goal=user_goal, steps=steps, strategy=strategy)

    def select_agents(self, user_goal: str) -> list[str]:
        """Return agent names selected for a goal without full plan construction."""
        plan = self.build_plan(user_goal)
        return [step.agent for step in plan.steps]
