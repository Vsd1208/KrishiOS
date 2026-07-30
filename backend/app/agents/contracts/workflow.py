"""Workflow definition contracts for reusable agent execution graphs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class WorkflowStepType(StrEnum):
    """Supported workflow step execution modes."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    RETRY = "retry"
    TIMEOUT = "timeout"
    HUMAN_APPROVAL = "human_approval"


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """A single node in a reusable workflow definition."""

    step_id: str
    agent_name: str
    action: str
    step_type: WorkflowStepType = WorkflowStepType.SEQUENTIAL
    depends_on: tuple[str, ...] = ()
    parameters: dict[str, Any] = field(default_factory=dict)
    condition: str | None = None
    max_iterations: int = 1
    timeout_seconds: float = 60.0
    fallback_agent: str | None = None
    requires_approval: bool = False


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    """Reusable workflow template composed of ordered steps."""

    workflow_id: str
    name: str
    description: str
    steps: tuple[WorkflowStep, ...]
    version: str = "1.0.0"
    default_timeout_seconds: float = 120.0


@dataclass(slots=True)
class WorkflowExecutionResult:
    """Aggregated outcome of a workflow run."""

    workflow_id: str
    status: str
    step_results: list[dict[str, Any]] = field(default_factory=list)
    merged_output: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    error_message: str | None = None
