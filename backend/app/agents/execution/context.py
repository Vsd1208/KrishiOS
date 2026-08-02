"""Execution context, trace tokens, and result structures for agents."""

import enum
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


class AgentStatus(str, enum.Enum):
    """Lifecycle status of an agent or task execution."""

    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    WAITING_FOR_TOOL = "waiting_for_tool"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


@dataclass(frozen=True, slots=True)
class AgentStepTrace:
    """A single trace record of an agent step or tool invocation."""

    step_number: int
    agent_name: str
    action: str
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    duration_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None


from app.api.dependencies.auth import AuthContext

@dataclass(slots=True)
class ExecutionContext:
    """Shared request context propagated across runtime, agents, and tools."""

    execution_id: UUID = field(default_factory=uuid4)
    session_id: str = "default_session"
    auth: AuthContext | None = None
    language: str = "en"
    state: str | None = None
    district: str | None = None
    crop: str | None = None
    season: str | None = None
    variables: dict[str, Any] = field(default_factory=dict)
    traces: list[AgentStepTrace] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def add_trace(self, trace: AgentStepTrace) -> None:
        """Append a step trace to the execution context."""
        self.traces.append(trace)


@dataclass(slots=True)
class ExecutionResult:
    """Standardized response contract produced by agents or workflows."""

    execution_id: UUID
    status: AgentStatus
    agent_name: str
    output: dict[str, Any]
    confidence_score: float
    grounded: bool
    citations: list[dict[str, Any]] = field(default_factory=list)
    traces: list[AgentStepTrace] = field(default_factory=list)
    duration_ms: float = 0.0
    error_message: str | None = None
