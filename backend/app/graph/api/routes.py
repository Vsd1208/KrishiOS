"""REST API endpoints for Graph Knowledge."""

from uuid import NAMESPACE_URL, uuid5

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission
from app.auth.permissions import Permission
from app.database.session import get_db_session
from app.graph.api.dependencies import get_graph_store
from app.graph.api.schemas import (
    GraphCandidateResponse,
    ReviewCandidateRequest,
)
from app.graph.ontology.relationships import is_allowed_triple
from app.models.graph_candidate import GraphKnowledgeCandidate


router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])


def _stable_node_id(label: str, canonical_name: str) -> str:
    """Generate a deterministic UUID for an ontology entity."""
    return str(uuid5(NAMESPACE_URL, f"krishios:{label}:{canonical_name.strip().lower()}"))


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
    context: AuthContext = Depends(
        RequirePermission(Permission.GRAPH_REVIEW)
    ),
    session: AsyncSession = Depends(get_db_session),
) -> GraphKnowledgeCandidate:
    """Approve or reject a graph knowledge candidate.

    APPROVE:
      1. Validate the candidate against the controlled ontology.
      2. Upsert subject and object nodes into Neo4j.
      3. Create the Neo4j relationship.
      4. Store the Neo4j relationship ID in PostgreSQL.
      5. Mark the candidate APPROVED.

    REJECT:
      Mark the candidate REJECTED and preserve the audit information.
    """
    result = await session.execute(
        select(GraphKnowledgeCandidate).where(
            GraphKnowledgeCandidate.id == candidate_id
        )
    )
    candidate = result.scalar_one_or_none()

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )

    if request.action not in {"APPROVE", "REJECT"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be APPROVE or REJECT",
        )

    # ------------------------------------------------------------------
    # Idempotency: an already reviewed candidate should not create
    # another Neo4j relationship.
    # ------------------------------------------------------------------
    if candidate.review_status in {"APPROVED", "REJECTED"}:
        return candidate

    # ------------------------------------------------------------------
    # REJECT
    # ------------------------------------------------------------------
    if request.action == "REJECT":
        candidate.review_status = "REJECTED"
        candidate.reviewed_by = context.user_uuid
        candidate.review_note = request.note

        await session.commit()
        await session.refresh(candidate)

        logger.info(
            "Officer {} rejected graph candidate {}",
            context.user_uuid,
            candidate_id,
        )
        return candidate

    # ------------------------------------------------------------------
    # APPROVE
    # ------------------------------------------------------------------

    # Validate the complete ontology triple before touching Neo4j.
    if not is_allowed_triple(
        candidate.subject_label,
        candidate.predicate,
        candidate.object_label,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Candidate relationship is not allowed by the ontology: "
                f"{candidate.subject_label} -[{candidate.predicate}]-> "
                f"{candidate.object_label}"
            ),
        )

    try:
        graph_store = get_graph_store()

        subject_node_id = _stable_node_id(
            candidate.subject_label,
            candidate.subject_name,
        )
        object_node_id = _stable_node_id(
            candidate.object_label,
            candidate.object_name,
        )

        # --------------------------------------------------------------
        # Create/update the subject node.
        # --------------------------------------------------------------
        await graph_store.upsert_node(
            label=candidate.subject_label,
            node_id=subject_node_id,
            properties={
                "canonical_name": candidate.subject_name.strip(),
                "status": "ACTIVE",
            },
        )

        # --------------------------------------------------------------
        # Create/update the object node.
        # --------------------------------------------------------------
        await graph_store.upsert_node(
            label=candidate.object_label,
            node_id=object_node_id,
            properties={
                "canonical_name": candidate.object_name.strip(),
                "status": "ACTIVE",
            },
        )

        # --------------------------------------------------------------
        # Create the relationship with complete provenance.
        # --------------------------------------------------------------
        edge = await graph_store.create_relationship(
            from_node_id=subject_node_id,
            rel_type=candidate.predicate,
            to_node_id=object_node_id,
            properties={
                "status": "ACTIVE",
                "source_document_uuid": str(candidate.document_uuid),
                "source_chunk_id": str(candidate.chunk_id),
                "page_number": candidate.page_number,
                "authority": candidate.authority,
                "confidence": candidate.confidence,
                "extraction_model": candidate.extraction_model,
                "source_text": candidate.source_text or "",
            },
        )

        # --------------------------------------------------------------
        # Persist the Neo4j relationship ID in PostgreSQL.
        # --------------------------------------------------------------
        candidate.neo4j_rel_id = edge.rel_id
        candidate.review_status = "APPROVED"
        candidate.reviewed_by = context.user_uuid
        candidate.review_note = request.note

        await session.commit()
        await session.refresh(candidate)

        logger.info(
            "Officer {} approved graph candidate {} and created Neo4j "
            "relationship {}",
            context.user_uuid,
            candidate_id,
            edge.rel_id,
        )

        return candidate

    except HTTPException:
        raise
    except Exception as exc:
        await session.rollback()

        logger.exception(
            "Failed to promote graph candidate {} into Neo4j",
            candidate_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to promote candidate into Neo4j: {exc}",
        ) from exc