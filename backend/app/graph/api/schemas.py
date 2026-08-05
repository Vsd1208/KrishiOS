"""Pydantic schemas for the Graph API."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GraphNodeSchema(BaseModel):
    """Schema for a graph node."""
    model_config = ConfigDict(from_attributes=True)

    node_id: str
    label: str
    canonical_name: str
    properties: dict[str, Any]


class EdgeProvenanceSchema(BaseModel):
    """Schema for edge provenance."""
    model_config = ConfigDict(from_attributes=True)

    source_document_uuid: str
    source_chunk_id: str
    page_number: int
    authority: str
    confidence: float
    extraction_model: str


class GraphEdgeSchema(BaseModel):
    """Schema for a graph edge."""
    model_config = ConfigDict(from_attributes=True)

    rel_id: str
    from_node_id: str
    to_node_id: str
    rel_type: str
    properties: dict[str, Any]
    provenance: EdgeProvenanceSchema | None = None


class GraphPathSchema(BaseModel):
    """Schema for a traversal path."""
    model_config = ConfigDict(from_attributes=True)

    nodes: list[GraphNodeSchema]
    edges: list[GraphEdgeSchema]
    path_text: str
    relevance_score: float


class GraphCandidateResponse(BaseModel):
    """Schema for returning candidate relationships for officer review."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_uuid: UUID
    chunk_id: UUID
    subject_label: str
    subject_name: str
    predicate: str
    object_label: str
    object_name: str
    confidence: float
    review_status: str
    neo4j_rel_id: str | None


class ReviewCandidateRequest(BaseModel):
    """Schema for approving or rejecting a candidate."""
    action: str = Field(..., description="'APPROVE' or 'REJECT'")
    note: str | None = None
