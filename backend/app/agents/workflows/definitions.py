"""Reusable workflow definitions for common agricultural tasks."""

from __future__ import annotations

from app.agents.contracts.workflow import WorkflowDefinition, WorkflowStep, WorkflowStepType


CROP_DIAGNOSIS_WORKFLOW = WorkflowDefinition(
    workflow_id="crop_diagnosis",
    name="Crop Diagnosis",
    description="Retrieve knowledge, generate advisory, and validate the response for crop health issues.",
    steps=(
        WorkflowStep(
            step_id="retrieve",
            agent_name="knowledge_retrieval_agent",
            action="search_knowledge",
            step_type=WorkflowStepType.PARALLEL,
            parameters={"top_k": 5},
        ),
        WorkflowStep(
            step_id="weather",
            agent_name="weather_intelligence_agent",
            action="inspect_weather",
            step_type=WorkflowStepType.PARALLEL,
        ),
        WorkflowStep(
            step_id="advise",
            agent_name="crop_advisory_agent",
            action="generate_advice",
            step_type=WorkflowStepType.SEQUENTIAL,
            depends_on=("retrieve",),
        ),
        WorkflowStep(
            step_id="validate",
            agent_name="response_validation_agent",
            action="validate_response",
            step_type=WorkflowStepType.SEQUENTIAL,
            depends_on=("advise",),
            parameters={"require_citations": True},
        ),
    ),
)

SCHEME_LOOKUP_WORKFLOW = WorkflowDefinition(
    workflow_id="scheme_lookup",
    name="Government Scheme Lookup",
    description="Search scheme documents and validate guidance for farmer eligibility queries.",
    steps=(
        WorkflowStep(
            step_id="scheme_search",
            agent_name="govt_scheme_agent",
            action="search_scheme_documents",
            step_type=WorkflowStepType.SEQUENTIAL,
        ),
        WorkflowStep(
            step_id="validate",
            agent_name="response_validation_agent",
            action="validate_response",
            step_type=WorkflowStepType.SEQUENTIAL,
            depends_on=("scheme_search",),
        ),
    ),
)

OFFICER_BRIEFING_WORKFLOW = WorkflowDefinition(
    workflow_id="officer_briefing",
    name="Officer Briefing",
    description="Generate administrative summaries for agricultural officers.",
    steps=(
        WorkflowStep(
            step_id="briefing",
            agent_name="officer_assistance_agent",
            action="generate_summary",
            step_type=WorkflowStepType.SEQUENTIAL,
            timeout_seconds=90.0,
        ),
        WorkflowStep(
            step_id="validate",
            agent_name="response_validation_agent",
            action="validate_response",
            step_type=WorkflowStepType.SEQUENTIAL,
            depends_on=("briefing",),
            requires_approval=False,
        ),
    ),
)

from app.agents.workflows.proactive_workflows import (
    DISEASE_RISK_WORKFLOW,
    MARKET_MOVEMENT_WORKFLOW,
    PROACTIVE_WORKFLOWS,
    SCHEME_NOTIFICATION_WORKFLOW,
    WEATHER_RISK_WORKFLOW,
)

BUILTIN_WORKFLOWS: dict[str, WorkflowDefinition] = {
    CROP_DIAGNOSIS_WORKFLOW.workflow_id: CROP_DIAGNOSIS_WORKFLOW,
    SCHEME_LOOKUP_WORKFLOW.workflow_id: SCHEME_LOOKUP_WORKFLOW,
    OFFICER_BRIEFING_WORKFLOW.workflow_id: OFFICER_BRIEFING_WORKFLOW,
    **PROACTIVE_WORKFLOWS,
}
