"""REST API endpoints for Graph Knowledge."""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission
from app.auth.permissions import Permission
from app.database.session import get_db_session
from app.graph.api.schemas import (
    GraphCandidateResponse,
    GraphNodeSchema,
    ReviewCandidateRequest,
)
from app.models.graph_candidate import GraphKnowledgeCandidate

# In a real app we'd inject GraphStore properly via dependencies,
# but for Sprint 6 MVP we will focus on the Postgres review workflow
# as the graph store might be accessed inside the agent tools.

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])


@router.get(
    "/candidates",
    response_model=list[GraphCandidateResponse],
    dependencies=[Depends(RequirePermission(Permission.GRAPH_REVIEW))],
)
async def list_candidates(
    status: str = "PENDING",
    session: AsyncSession = Depends(get_db_session),
) -> list[GraphKnowledgeCandidate]:
    """List knowledge candidates for officer review."""
    result = await session.execute(
        select(GraphKnowledgeCandidate)
        .where(GraphKnowledgeCandidate.review_status == status)
        .order_by(GraphKnowledgeCandidate.created_at.desc())
        .limit(100)
    )
    return list(result.scalars().all())


@router.post(
    "/candidates/{candidate_id}/review",
    response_model=GraphCandidateResponse,
    dependencies=[Depends(RequirePermission(Permission.GRAPH_REVIEW))],
)
async def review_candidate(
    candidate_id: int,
    request: ReviewCandidateRequest,
    context: AuthContext = Depends(RequirePermission(Permission.GRAPH_REVIEW)),
    session: AsyncSession = Depends(get_db_session),
) -> GraphKnowledgeCandidate:
    """Approve or reject a graph knowledge candidate.
    
    If approved, this would trigger the actual insertion into Neo4j.
    For MVP, we just update the Postgres state.
    """
    result = await session.execute(
        select(GraphKnowledgeCandidate).where(GraphKnowledgeCandidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )

    if request.action not in ["APPROVE", "REJECT"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be APPROVE or REJECT",
        )

    candidate.review_status = "APPROVED" if request.action == "APPROVE" else "REJECTED"
    candidate.reviewed_by = context.user_uuid
    candidate.review_note = request.note

    # In a full implementation, if action == APPROVE, we would call:
    # rel = await graph_store.create_relationship(...)
    # candidate.neo4j_rel_id = rel.rel_id

    await session.commit()
    await session.refresh(candidate)
    
    logger.info("Officer {} {} candidate {}", context.user_uuid, request.action, candidate_id)
    return candidate
