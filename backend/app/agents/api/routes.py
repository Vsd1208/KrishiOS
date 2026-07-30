"""HTTP routes for agent runtime execution and discovery."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.api.schemas import (
    AgentExecutionRequest,
    AgentExecutionResponse,
    AgentInfoResponse,
    AgentResultItem,
    RuntimeStatusResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
)
from app.agents.execution.context import ExecutionContext
from app.agents.runtime.factory import get_runtime_engine
from app.agents.runtime.engine import AgentRuntimeEngine

router = APIRouter(tags=["Agent Runtime"])


def _get_runtime() -> AgentRuntimeEngine:
    """Dependency that returns the process-wide runtime engine."""
    return get_runtime_engine()


@router.post("/agents/execute", response_model=AgentExecutionResponse, status_code=status.HTTP_200_OK)
async def execute_agent(
    request: AgentExecutionRequest,
    runtime: Annotated[AgentRuntimeEngine, Depends(_get_runtime)],
) -> AgentExecutionResponse:
    """Execute the agent runtime for a user goal."""
    context = ExecutionContext(
        session_id=request.session_id or "default",
        state=request.state,
        district=request.district,
        crop=request.crop,
        season=request.season,
    )
    results = await runtime.execute(request.goal, request.session_id, context)

    result_items = [
        AgentResultItem(
            agent=r.agent_name,
            status=r.status.value,
            output=r.output,
            confidence=r.confidence_score,
            grounded=r.grounded,
            citations=r.citations,
            error=r.error_message,
        )
        for r in results
    ]

    overall_status = "completed" if all(r.status.value == "completed" for r in results) else "partial"
    execution_id = str(results[0].execution_id) if results else "none"

    return AgentExecutionResponse(
        goal=request.goal,
        status=overall_status,
        execution_id=execution_id,
        results=result_items,
        evaluation=runtime.evaluate_results(results),
    )


@router.post("/workflows/run", response_model=WorkflowRunResponse, status_code=status.HTTP_200_OK)
async def run_workflow(
    request: WorkflowRunRequest,
    runtime: Annotated[AgentRuntimeEngine, Depends(_get_runtime)],
) -> WorkflowRunResponse:
    """Execute a registered workflow definition."""
    workflow = runtime.workflows().get(request.workflow_id)
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{request.workflow_id}' not found",
        )

    result = await runtime.run_workflow(
        workflow_id=request.workflow_id,
        goal=request.goal,
        session_id=request.session_id,
        parameters=request.parameters,
        approved_steps=set(request.approved_steps),
    )

    return WorkflowRunResponse(
        workflow_id=result.workflow_id,
        status=result.status,
        step_results=result.step_results,
        merged_output=result.merged_output,
        duration_ms=result.duration_ms,
    )


@router.get("/agents", response_model=list[AgentInfoResponse], status_code=status.HTTP_200_OK)
async def list_agents(
    runtime: Annotated[AgentRuntimeEngine, Depends(_get_runtime)],
) -> list[AgentInfoResponse]:
    """List registered agents."""
    return [
        AgentInfoResponse(
            name=metadata.name,
            description=metadata.description,
            capabilities=metadata.capabilities,
            supported_tools=metadata.supported_tools,
            priority=metadata.priority,
            version=metadata.version,
            health_status=metadata.health_status,
        )
        for metadata in runtime.registry().list_metadata()
    ]


@router.get("/agents/{agent_id}", response_model=AgentInfoResponse, status_code=status.HTTP_200_OK)
async def get_agent(
    agent_id: str,
    runtime: Annotated[AgentRuntimeEngine, Depends(_get_runtime)],
) -> AgentInfoResponse:
    """Return metadata and health for a specific agent."""
    agent = runtime.registry().get(agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )
    metadata = agent.metadata
    health = await agent.health()
    return AgentInfoResponse(
        name=metadata.name,
        description=metadata.description,
        capabilities=metadata.capabilities,
        supported_tools=metadata.supported_tools,
        priority=metadata.priority,
        version=metadata.version,
        health_status=str(health.get("status", metadata.health_status)),
    )


@router.get("/runtime/status", response_model=RuntimeStatusResponse, status_code=status.HTTP_200_OK)
async def runtime_status(
    runtime: Annotated[AgentRuntimeEngine, Depends(_get_runtime)],
) -> RuntimeStatusResponse:
    """Return runtime health and metrics summary."""
    health = await runtime.health_check()
    return RuntimeStatusResponse(
        status=str(health["status"]),
        uptime_seconds=float(health["uptime_seconds"]),
        registered_agents=int(health["registered_agents"]),
        registered_tools=int(health["registered_tools"]),
        unhealthy_agents=list(health["unhealthy_agents"]),
        metrics=dict(health["metrics"]),
    )
