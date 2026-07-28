"""Unit & integration tests for Knowledge Documents API schemas and models."""

import pytest
from app.models.knowledge_document import DocumentStatus, KnowledgeDocument
from app.schemas.knowledge import (
    DocumentUploadMetadata,
    SearchFilters,
    SearchRequest,
)


def test_document_upload_metadata_validation() -> None:
    meta = DocumentUploadMetadata(
        title="ICAR Wheat Guide",
        crop="Wheat",
        season="RABI",
    )
    assert meta.season == "rabi"


def test_invalid_season_validation() -> None:
    with pytest.raises(ValueError, match="season must be one of"):
        DocumentUploadMetadata(
            title="Test",
            season="summer_season",
        )


def test_search_request_schema() -> None:
    req = SearchRequest(
        query="wheat rust treatment",
        top_k=10,
        filters=SearchFilters(crop="wheat", season="rabi"),
    )
    assert req.query == "wheat rust treatment"
    assert req.top_k == 10
    assert req.filters.crop == "wheat"


def test_knowledge_document_status_enum() -> None:
    assert DocumentStatus.PENDING.value == "pending"
    assert DocumentStatus.COMPLETED.value == "completed"
    assert DocumentStatus.FAILED.value == "failed"
