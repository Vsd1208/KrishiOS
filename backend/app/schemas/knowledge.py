"""Pydantic v2 schemas for the Knowledge Infrastructure API.

Covers document upload, document listing, search requests, and
search responses. No SQLAlchemy models are exposed directly.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


# ── Upload ────────────────────────────────────────────────────────────────────


class DocumentUploadMetadata(BaseModel):
    """Optional metadata submitted alongside a file upload.

    All fields are optional. The ingestion pipeline will attempt to
    derive missing fields (e.g. language) from the document content.
    """

    title: str = Field(max_length=500, description="Human-readable document title")
    document_type: str = Field(
        default="general",
        max_length=100,
        description="Category: advisory, guideline, research, scheme, etc.",
    )
    language: str = Field(
        default="en",
        max_length=50,
        description="BCP-47 language code, e.g. 'en', 'hi', 'ta'",
    )
    source: str | None = Field(default=None, max_length=300)
    source_url: str | None = Field(default=None)
    authority: str | None = Field(
        default=None,
        max_length=300,
        description="Issuing body, e.g. ICAR, NABARD",
    )
    state: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=150)
    crop: str | None = Field(default=None, max_length=150)
    season: str | None = Field(
        default=None,
        max_length=50,
        description="kharif | rabi | zaid | perennial",
    )
    uploaded_by: str | None = Field(default=None, max_length=150)

    @field_validator("season")
    @classmethod
    def validate_season(cls, v: str | None) -> str | None:
        allowed = {"kharif", "rabi", "zaid", "perennial"}
        if v is not None and v.lower() not in allowed:
            msg = f"season must be one of {sorted(allowed)}"
            raise ValueError(msg)
        return v.lower() if v else v


# ── Document responses ────────────────────────────────────────────────────────


class DocumentResponse(BaseModel):
    """Public representation of an ingested KnowledgeDocument."""

    model_config = {"from_attributes": True}

    id: int
    uuid: UUID
    title: str
    document_type: str
    language: str
    source: str | None
    authority: str | None
    state: str | None
    district: str | None
    crop: str | None
    season: str | None
    uploaded_by: str | None
    file_hash: str
    file_size: int
    mime_type: str
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    total: int
    offset: int
    limit: int
    items: list[DocumentResponse]


class DocumentUploadResponse(BaseModel):
    """Immediate response returned after a successful upload."""

    document_id: int
    uuid: UUID
    title: str
    status: str
    message: str = "Document accepted for ingestion. Track status via GET /documents/{id}."


# ── Chunk response ────────────────────────────────────────────────────────────


class ChunkResponse(BaseModel):
    """A chunk returned as part of a search result."""

    model_config = {"from_attributes": True}

    chunk_id: UUID
    chunk_index: int
    chunk_text: str
    page_number: int
    token_count: int
    metadata_json: dict | None


# ── Search ────────────────────────────────────────────────────────────────────


class SearchFilters(BaseModel):
    """Optional metadata filters for a semantic search request.

    All fields are optional. Non-None values are combined with AND
    logic in Qdrant's payload filter.
    """

    language: str | None = None
    crop: str | None = None
    district: str | None = None
    state: str | None = None
    season: str | None = None
    authority: str | None = None
    document_id: str | None = None


class SearchRequest(BaseModel):
    """Request body for the semantic search endpoint."""

    query: str = Field(
        min_length=3,
        max_length=2000,
        description="Natural language query to embed and search",
    )
    filters: SearchFilters = Field(default_factory=SearchFilters)
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return")
    score_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity to include in results",
    )


class SearchHit(BaseModel):
    """One result entry in a semantic search response."""

    score: float
    page_number: int
    chunk: ChunkResponse
    document: DocumentResponse
    metadata: dict | None


class SearchResponse(BaseModel):
    """Full semantic search response."""

    query: str
    top_k: int
    total_hits: int
    hits: list[SearchHit]
