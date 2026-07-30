"""Pydantic schemas for agent runtime APIs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentExecutionRequest(BaseModel):
    """Request for executing an agent-powered workflow."""

    goal: str = Field(min_length=3, max_length=4000)
    session_id: str | None = None


class AgentExecutionResponse(BaseModel):
    """Response body for agent execution."""

    goal: str
    status: str
    results: list[dict[str, object]]
