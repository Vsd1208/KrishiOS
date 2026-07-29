"""SQLAlchemy ORM models for the KrishiOS domain.

Sprint 0 / Sprint 1 — Domain models
Sprint 2            — Knowledge infrastructure models
"""

from app.models.crop import Crop
from app.models.district import District
from app.models.document_chunk import DocumentChunk
from app.models.farmer import Farmer
from app.models.field import Field
from app.models.field_crop import FieldCrop, FieldCropStatus
from app.models.knowledge_document import DocumentStatus, KnowledgeDocument
from app.models.officer import Officer
from app.models.retrieval_index import (
    IndexedDocumentState,
    RetrievalBuildMode,
    RetrievalIndexKind,
    RetrievalIndexStatus,
    RetrievalIndexVersion,
)
from app.models.soil_sample import SoilSample, SoilSampleStatus

__all__ = [
    # Sprint 0/1 — domain
    "Crop",
    "District",
    "Farmer",
    "Field",
    "FieldCrop",
    "FieldCropStatus",
    "Officer",
    "SoilSample",
    "SoilSampleStatus",
    # Sprint 2 — knowledge
    "DocumentChunk",
    "DocumentStatus",
    "IndexedDocumentState",
    "KnowledgeDocument",
    "RetrievalBuildMode",
    "RetrievalIndexKind",
    "RetrievalIndexStatus",
    "RetrievalIndexVersion",
]
