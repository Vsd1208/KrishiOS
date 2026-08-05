"""Extracts entities from user queries to seed graph traversal.

Reuses the same DictionaryEntityExtractor and EntityResolver used during
ingestion so that query entities exactly match graph entities.
"""

from __future__ import annotations

from app.graph.extraction.entity_extractor import DictionaryEntityExtractor
from app.graph.extraction.entity_resolver import EntityResolver
from app.graph.extraction.types import ResolvedEntity


class QueryEntityExtractor:
    """Extracts and resolves entities from a natural language query."""

    def __init__(self) -> None:
        self._extractor = DictionaryEntityExtractor()
        self._resolver = EntityResolver()

    async def extract(self, query: str) -> list[ResolvedEntity]:
        """Extract and resolve entities from the query."""
        # Empty metadata context because queries don't have document metadata
        raw_entities = await self._extractor.extract(query, document_metadata={})
        resolved = self._resolver.resolve_bulk(raw_entities)
        
        # Deduplicate resolved entities (same canonical name and type)
        unique: dict[tuple[str, str], ResolvedEntity] = {}
        for ent in resolved:
            key = (ent.entity_type, ent.canonical_name)
            if key not in unique or ent.confidence > unique[key].confidence:
                unique[key] = ent
                
        return list(unique.values())
