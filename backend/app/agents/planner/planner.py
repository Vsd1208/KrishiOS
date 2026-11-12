"""Structured planning engine for agent workflow generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.contracts.workflow import WorkflowStepType
from app.nlu.types import Intent, NLUResult


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


# Intents answered from the knowledge base (RAG/GraphRAG) plus the advisory agent.
_KNOWLEDGE_INTENTS = {
    Intent.ADVISORY, Intent.DISEASE, Intent.GOVT_BULLETIN, Intent.YIELD, Intent.MARKET,
}


class PlanningEngine:
    """Generate structured execution plans for agricultural reasoning tasks.

    Sprint 11: routing uses multilingual NLU output (intent + secondary intents) instead of
    English keyword tuples, so Telugu/Hindi/code-switched goals route correctly, "yield
    forecast" is never sent to the weather agent, and naming a district no longer triggers
    the officer agent.
    """

    def build_plan(self, user_goal: str, nlu: NLUResult | None = None) -> ExecutionPlan:
        """Create a structured plan from the goal and its NLU parse (parsed here if absent)."""
        if nlu is None:
            from app.nlu.service import parse_sync  # noqa: PLC0415 - avoid import cycle

            nlu = parse_sync(user_goal)
        intents = {nlu.intent, *nlu.secondary_intents}
        nlu_params: dict[str, Any] = {
            "intent": nlu.intent.value,
            "language": nlu.language,
            "crop_canonical": nlu.entities.crop,
            "district_lgd_code": nlu.entities.district_lgd_code,
        }
        if nlu.entities.crop:
            from app.catalog import get_crop_catalog  # noqa: PLC0415

            entry = get_crop_catalog().get(nlu.entities.crop)
            # Knowledge-base metadata uses English crop names ("Paddy", "Cotton").
            nlu_params["crop"] = entry.name_en.split("(")[0].strip() if entry else None
        steps: list[PlanStep] = []
        step_counter = 0

        def _next_id(prefix: str) -> str:
            nonlocal step_counter
            step_counter += 1
            return f"{prefix}_{step_counter}"

        needs_knowledge = bool(intents & _KNOWLEDGE_INTENTS)
        needs_weather = Intent.WEATHER in intents
        needs_scheme = Intent.SCHEME in intents
        needs_officer = Intent.OFFICER in intents

        parallel_steps: list[PlanStep] = []

        if needs_weather:
            parallel_steps.append(
                PlanStep(
                    step_id=_next_id("weather"),
                    agent="weather_intelligence_agent",
                    action="inspect_weather",
                    step_type=WorkflowStepType.PARALLEL,
                    parameters={"goal": user_goal, **nlu_params},
                )
            )

        if needs_scheme:
            parallel_steps.append(
                PlanStep(
                    step_id=_next_id("scheme"),
                    agent="govt_scheme_agent",
                    action="search_scheme_documents",
                    step_type=WorkflowStepType.PARALLEL,
                    parameters={"goal": user_goal, **nlu_params},
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
                    parameters={"goal": user_goal, "query": user_goal, **nlu_params},
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
                    parameters={"goal": user_goal, "query": user_goal, **nlu_params},
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
                    parameters={"goal": user_goal, "task": user_goal, **nlu_params},
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
