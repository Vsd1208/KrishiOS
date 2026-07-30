"""Pydantic schemas for agent runtime APIs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentExecutionRequest(BaseModel):
    """Request for executing an agent-powered workflow."""

    goal: str = Field(min_length=3, max_length=4000)
    session_id: str | None = None
    state: str | None = None
    district: str | None = None
    crop: str | None = None
    season: str | None = None


class AgentResultItem(BaseModel):
    """Single agent result in an execution response."""

    agent: str
    status: str
    output: dict[str, Any]
    confidence: float = 0.0
    grounded: bool = False
    citations: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class AgentExecutionResponse(BaseModel):
    """Response body for agent execution."""

    goal: str
    status: str
    execution_id: str
    results: list[AgentResultItem]
    evaluation: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunRequest(BaseModel):
    """Request for running a predefined workflow."""

    workflow_id: str = Field(min_length=1, max_length=128)
    goal: str = Field(min_length=3, max_length=4000)
    session_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    approved_steps: list[str] = Field(default_factory=list)


class WorkflowRunResponse(BaseModel):
    """Response body for workflow execution."""

    workflow_id: str
    status: str
    step_results: list[dict[str, Any]]
    merged_output: dict[str, Any]
    duration_ms: float


class AgentInfoResponse(BaseModel):
    """Agent metadata returned by discovery endpoints."""

    name: str
    description: str
    capabilities: list[str]
    supported_tools: list[str]
    priority: int
    version: str
    health_status: str


class RuntimeStatusResponse(BaseModel):
    """Runtime health and metrics summary."""

    status: str
    uptime_seconds: float
    registered_agents: int
    registered_tools: int
    unhealthy_agents: list[str]
    metrics: dict[str, float]
