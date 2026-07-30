"""Typed event contracts for the internal agent event bus."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class AgentEvent:
    """Event emitted during agent execution, tool handling, or workflow transitions."""

    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    source: str = "runtime"


class EventTypes:
    """Standard event type constants for the agent runtime."""

    DOCUMENT_INDEXED = "document.indexed"
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TOOL_STARTED = "tool.started"
    TOOL_FAILED = "tool.failed"
    TOOL_COMPLETED = "tool.completed"
    WEATHER_UPDATED = "weather.updated"
    KNOWLEDGE_REFRESHED = "knowledge.refreshed"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    PLAN_CREATED = "plan.created"
    GUARDRAIL_REJECTED = "guardrail.rejected"
