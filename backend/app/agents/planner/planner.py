"""Structured planning engine for agent workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PlanStep:
    """A single step in an execution plan."""

    agent: str
    action: str
    depends_on: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExecutionPlan:
    """Structured execution plan for a user-given goal."""

    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    strategy: str = "sequential"


class PlanningEngine:
    """Generate execution plans for agricultural reasoning tasks."""

    def build_plan(self, user_goal: str) -> ExecutionPlan:
        """Create a structured plan based on the user goal."""
        goal_lower = user_goal.casefold()
        steps: list[PlanStep] = []

        if "weather" in goal_lower:
            steps.append(PlanStep(agent="weather_intelligence", action="inspect_weather", parameters={"goal": user_goal}))
        if "scheme" in goal_lower or "subsid" in goal_lower or "government" in goal_lower:
            steps.append(PlanStep(agent="government_scheme", action="search_scheme_documents", parameters={"goal": user_goal}))
        if "yellow" in goal_lower or "disease" in goal_lower or "paddy" in goal_lower:
            steps.append(PlanStep(agent="knowledge_retrieval", action="search_knowledge", parameters={"goal": user_goal}))
            steps.append(PlanStep(agent="crop_advisory", action="generate_advice", parameters={"goal": user_goal}))
        steps.append(PlanStep(agent="response_validation", action="validate_response", parameters={"goal": user_goal}))

        return ExecutionPlan(goal=user_goal, steps=steps, strategy="sequential")
