"""Pydantic contracts for Sprint 3 retrieval and index APIs."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.retrieval_index import RetrievalBuildMode, RetrievalIndexKind, RetrievalIndexStatus


class IndexBuildRequest(BaseModel):
    """Request body for building a new retrieval index version."""

    index_kind: RetrievalIndexKind = RetrievalIndexKind.BASE
    build_mode: RetrievalBuildMode = RetrievalBuildMode.BLUE_GREEN
    alias_name: str = Field(default="krishios-live", min_length=3, max_length=200)
    source_document_type: str | None = Field(default=None, max_length=100)


class IndexPromoteRequest(BaseModel):
    """Request body for promoting a validated index."""

    index_id: int = Field(gt=0)


class IndexRollbackRequest(BaseModel):
    """Request body for alias-based rollback."""

    alias_name: str = Field(default="krishios-live", min_length=3, max_length=200)


class IndexResponse(BaseModel):
    """Public representation of a retrieval index version."""

    model_config = {"from_attributes": True}

    id: int
    version_number: int
    collection_name: str
    alias_name: str
    index_kind: RetrievalIndexKind
    status: RetrievalIndexStatus
    build_mode: RetrievalBuildMode
    embedding_model: str
    embedding_version: str
    vector_size: int
    chunk_count: int
    document_count: int
    validation_report: dict | None
    promoted_at: datetime | None
    rolled_back_at: datetime | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


class IndexStatusResponse(BaseModel):
    """Current production alias and version history."""

    alias_name: str
    active_collection: str | None
    active_index: IndexResponse | None
    previous_index: IndexResponse | None
    indexes: list[IndexResponse]


class RetrievalSearchFilters(BaseModel):
    """Metadata filters for enterprise retrieval."""

    crop: str | None = None
    state: str | None = None
    district: str | None = None
    season: str | None = None
    language: str | None = None
    authority: str | None = None
    document_type: str | None = None
    effective_at: datetime | None = None


class RetrievalSearchRequest(BaseModel):
    """Request body for enterprise semantic retrieval."""

    query: str = Field(min_length=3, max_length=2000)
    filters: RetrievalSearchFilters = Field(default_factory=RetrievalSearchFilters)
    top_k: int = Field(default=10, ge=1, le=100)
    score_threshold: float = Field(default=0.25, ge=0, le=1)
    include_delta: bool = True


class CitationResponse(BaseModel):
    """Citation attached to a retrieval result."""

    document_id: int | None
    title: str | None
    source: str | None
    source_url: str | None
    page_number: int | None
    chunk_id: str


class RetrievalResultResponse(BaseModel):
    """One ranked retrieval result."""

    answer_context: str
    chunk: str
    similarity: float
    ranking_score: float
    freshness_score: float
    authority_score: float
    document: dict[str, object | None]
    page: int | None
    chunk_id: str
    collection: str
    version: str | None
    metadata: dict[str, object]
    citation: CitationResponse


class RetrievalSearchResponse(BaseModel):
    """Enterprise retrieval response without LLM answer generation."""

    query: str
    total_results: int
    latency_ms: float
    results: list[RetrievalResultResponse]
