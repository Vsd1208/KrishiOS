"""Data types produced by entity and relationship extraction.

These are intermediate types — they represent *candidates* before
resolution and validation, not finalized graph nodes/edges.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ExtractedEntity:
    """A candidate entity extracted from document text.

    Attributes:
        raw_text:       The exact span of text that triggered extraction.
        entity_type:    Candidate ontology label (e.g. "Crop", "Disease").
        canonical_name: Name after normalization — empty until resolved.
        confidence:     Extraction confidence (0.0–1.0).
        matched_via:    How it was found: "canonical" | "alias" | "pattern".
        position:       Character offset in the source text (for provenance).
    """

    raw_text: str
    entity_type: str
    canonical_name: str = ""
    confidence: float = 0.0
    matched_via: str = "pattern"
    position: int = 0


@dataclass(slots=True)
class ResolvedEntity:
    """An entity after canonical resolution — ready for graph insertion."""

    canonical_name: str
    entity_type: str
    confidence: float
    input_string: str
    matched_via: str   # "canonical" | "alias" | "fuzzy"
    aliases: list[str] = field(default_factory=list)
    scientific_name: str = ""


@dataclass(slots=True)
class ExtractedRelationship:
    """A candidate relationship between two resolved entities.

    Attributes:
        subject:          The resolved source entity.
        predicate:        Relationship type string (must be in ALLOWED_RELATIONSHIPS).
        obj:              The resolved target entity.
        confidence:       Extraction confidence (0.0–1.0).
        source_text:      The text span that evidence this relationship.
        source_chunk_id:  UUID of the DocumentChunk this came from.
        document_uuid:    UUID of the parent KnowledgeDocument.
        page_number:      Source page number.
        authority:        Publishing authority from document metadata.
        extraction_model: Identifier of the extractor that produced this.
    """

    subject: ResolvedEntity
    predicate: str
    obj: ResolvedEntity
    confidence: float
    source_text: str
    source_chunk_id: str
    document_uuid: str
    page_number: int
    authority: str
    extraction_model: str = "dictionary_pattern_v1"
