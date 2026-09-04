"""Graph extraction stage for the ingestion pipeline.

This stage runs AFTER vector indexing. It orchestrates:
  Chunk Text → Entity Extractor → Entity Resolver → 
  Relationship Extractor → Validator → GraphKnowledgeCandidate (PostgreSQL)

It does NOT insert directly into Neo4j. It creates candidates in Postgres
so that they can be reviewed by an officer or auto-promoted by a background task.
"""

from __future__ import annotations

from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.extraction.entity_extractor import DictionaryEntityExtractor
from app.graph.extraction.entity_resolver import EntityResolver
from app.graph.extraction.relationship_extractor import PatternRelationshipExtractor
from app.graph.validation.relationship_validator import RelationshipValidator
from app.knowledge.interfaces.chunker import TextChunk
from app.models.knowledge_document import KnowledgeDocument


class GraphIngestionStage:
    """Orchestrates graph knowledge extraction from document chunks.

    Designed to be run as the final stage of the main IngestionPipeline.
    A failure here should be caught so it doesn't fail the entire document
    ingestion (vector indexing may have already succeeded).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._entity_extractor = DictionaryEntityExtractor()
        self._entity_resolver = EntityResolver()
        self._rel_extractor = PatternRelationshipExtractor()
        self._validator = RelationshipValidator()

    async def run(
        self,
        doc: KnowledgeDocument,
        chunks: list[TextChunk],
        chunk_uuids: list[UUID],
    ) -> None:
        """Run graph extraction over all chunks and save candidates.

        Args:
            doc: The KnowledgeDocument being ingested.
            chunks: The text chunks produced by the chunker.
            chunk_uuids: The corresponding UUIDs (point_ids) for each chunk.
        """
        logger.info("GraphIngestionStage: starting for document_id={}", doc.id)
        
        # We need the GraphKnowledgeCandidate model, which we'll import here
        # to avoid circular dependencies if it's imported at the top level
        # before the models module is fully loaded.
        from app.models.graph_candidate import GraphKnowledgeCandidate

        # Build document metadata for seeding
        doc_metadata = {
            "crop": doc.crop,
            "season": doc.season,
            "authority": doc.authority,
            "document_uuid": str(doc.uuid),
        }

        total_candidates = 0

        for chunk, chunk_uuid in zip(chunks, chunk_uuids, strict=True):
            try:
                # 1. Extract raw entities
                raw_entities = await self._entity_extractor.extract(
                    text=chunk.text,
                    document_metadata=doc_metadata,
                )
                if not raw_entities:
                    continue

                # 2. Resolve to canonical names
                resolved_entities = self._entity_resolver.resolve_bulk(raw_entities)
                if not resolved_entities:
                    continue

                # 3. Extract relationships
                raw_rels = await self._rel_extractor.extract(
                    entities=resolved_entities,
                    text=chunk.text,
                    document_metadata=doc_metadata,
                )

                # 4. Validate against ontology
                valid_rels = self._validator.validate(raw_rels)
                
                # 5. Create candidates in Postgres
                for rel in valid_rels:
                    # Determine initial review status based on confidence
                    from app.config.settings import get_settings
                    settings = get_settings()
                    
                    status = "PENDING" # Default for review
                    if rel.confidence >= settings.GRAPH_AUTO_ACCEPT_THRESHOLD:
                        status = "APPROVED"
                    elif rel.confidence < settings.GRAPH_REVIEW_REQUIRED_THRESHOLD:
                        status = "REJECTED" # We might not even save these, but let's log them as rejected
                        
                    candidate = GraphKnowledgeCandidate(
                        document_uuid=doc.uuid,
                        chunk_id=chunk_uuid,
                        subject_label=rel.subject.entity_type,
                        subject_name=rel.subject.canonical_name,
                        predicate=rel.predicate,
                        object_label=rel.obj.entity_type,
                        object_name=rel.obj.canonical_name,
                        confidence=rel.confidence,
                        extraction_model=rel.extraction_model,
                        review_status=status,
                    )
                    self._session.add(candidate)
                    total_candidates += 1

            except Exception as exc:
                logger.warning(
                    "GraphIngestionStage: failed on chunk {} of document_id={}: {}",
                    chunk.chunk_index,
                    doc.id,
                    exc
                )

        # Flush the session to persist candidates
        await self._session.flush()
        logger.info(
            "GraphIngestionStage: finished document_id={} with {} candidates",
            doc.id,
            total_candidates
        )
