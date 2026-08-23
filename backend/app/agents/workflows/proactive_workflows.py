"""Reusable Proactive Decision Intelligence Workflow Definitions."""

from __future__ import annotations

from app.agents.contracts.workflow import WorkflowDefinition, WorkflowStep, WorkflowStepType

WEATHER_RISK_WORKFLOW = WorkflowDefinition(
    workflow_id="proactive_weather_risk",
    name="Proactive Weather Risk Advisory Workflow",
    description="Inspect weather telemetry, synthesize risk advisory, and validate response for farmers.",
    steps=(
        WorkflowStep(
            step_id="weather_check",
            agent_name="weather_intelligence_agent",
            action="inspect_weather",
            step_type=WorkflowStepType.SEQUENTIAL,
        ),
        WorkflowStep(
            step_id="synthesize_advisory",
            agent_name="proactive_intelligence_agent",
            action="synthesize_proactive_advisory",
            step_type=WorkflowStepType.SEQUENTIAL,
            depends_on=("weather_check",),
        ),
        WorkflowStep(
            step_id="validate",
            agent_name="response_validation_agent",
            action="validate_response",
            step_type=WorkflowStepType.SEQUENTIAL,
            depends_on=("synthesize_advisory",),
        ),
    ),
)

DISEASE_RISK_WORKFLOW = WorkflowDefinition(
    workflow_id="proactive_disease_risk",
    name="Proactive Disease & Microclimate Risk Workflow",
    description="Retrieve knowledge graph and vector evidence, evaluate microclimate, and generate advisory.",
    steps=(
        WorkflowStep(
            step_id="retrieve_evidence",
            agent_name="knowledge_retrieval_agent",
            action="search_knowledge",
            step_type=WorkflowStepType.SEQUENTIAL,
            parameters={"top_k": 3},
        ),
        WorkflowStep(
            step_id="synthesize_advisory",
            agent_name="proactive_intelligence_agent",
            action="synthesize_proactive_advisory",
            step_type=WorkflowStepType.SEQUENTIAL,
            depends_on=("retrieve_evidence",),
        ),
        WorkflowStep(
            step_id="validate",
            agent_name="response_validation_agent",
            action="validate_response",
            step_type=WorkflowStepType.SEQUENTIAL,
            depends_on=("synthesize_advisory",),
        ),
    ),
)

MARKET_MOVEMENT_WORKFLOW = WorkflowDefinition(
    workflow_id="proactive_market_movement",
    name="Proactive Market Movement Workflow",
    description="Synthesize price shift advisory and validate recommendation without financial speculation.",
    steps=(
        WorkflowStep(
            step_id="synthesize_advisory",
            agent_name="proactive_intelligence_agent",
            action="synthesize_proactive_advisory",
            step_type=WorkflowStepType.SEQUENTIAL,
        ),
        WorkflowStep(
            step_id="validate",
            agent_name="response_validation_agent",
            action="validate_response",
            step_type=WorkflowStepType.SEQUENTIAL,
            depends_on=("synthesize_advisory",),
        ),
    ),
)

SCHEME_NOTIFICATION_WORKFLOW = WorkflowDefinition(
    workflow_id="proactive_scheme_notification",
    name="Proactive Government Scheme Eligibility Workflow",
    description="Match scheme eligibility criteria and generate informational advisory for farmers.",
    steps=(
        WorkflowStep(
            step_id="scheme_search",
            agent_name="govt_scheme_agent",
            action="search_scheme_documents",
            step_type=WorkflowStepType.SEQUENTIAL,
        ),
        WorkflowStep(
            step_id="synthesize_advisory",
            agent_name="proactive_intelligence_agent",
            action="synthesize_proactive_advisory",
            step_type=WorkflowStepType.SEQUENTIAL,
            depends_on=("scheme_search",),
        ),
        WorkflowStep(
            step_id="validate",
            agent_name="response_validation_agent",
            action="validate_response",
            step_type=WorkflowStepType.SEQUENTIAL,
            depends_on=("synthesize_advisory",),
        ),
    ),
)

PROACTIVE_WORKFLOWS: dict[str, WorkflowDefinition] = {
    WEATHER_RISK_WORKFLOW.workflow_id: WEATHER_RISK_WORKFLOW,
    DISEASE_RISK_WORKFLOW.workflow_id: DISEASE_RISK_WORKFLOW,
    MARKET_MOVEMENT_WORKFLOW.workflow_id: MARKET_MOVEMENT_WORKFLOW,
    SCHEME_NOTIFICATION_WORKFLOW.workflow_id: SCHEME_NOTIFICATION_WORKFLOW,
}
