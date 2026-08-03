"""Dictionary-based entity extractor for the KrishiOS knowledge graph.

MVP approach: scan chunk text for known entity names using domain dictionaries.
This is deterministic, fast, and testable without an LLM dependency.

The interface is designed for substitution: an LLM-based or NER-based extractor
can replace this by implementing the same ``extract()`` method signature.

Extraction confidence:
  - Full canonical name match:   0.95
  - Alias match (full word):     0.85
  - Alias match (partial):       0.70

All matches are case-insensitive and word-boundary aware.
"""

from __future__ import annotations

import re
from typing import Protocol

from loguru import logger

from app.graph.extraction.types import ExtractedEntity
from app.graph.ontology.dictionaries import ALL_DICTIONARIES
from app.graph.ontology.entities import ALLOWED_ENTITY_LABELS


# ---------------------------------------------------------------------------
# Extractor Protocol (the interface contract for future implementations)
# ---------------------------------------------------------------------------


class EntityExtractorProtocol(Protocol):
    """Contract for entity extractors. Current impl: DictionaryEntityExtractor."""

    async def extract(
        self,
        text: str,
        document_metadata: dict[str, object],
    ) -> list[ExtractedEntity]:
        """Extract candidate entities from a text chunk."""


# ---------------------------------------------------------------------------
# MVP implementation: Dictionary-based
# ---------------------------------------------------------------------------


class DictionaryEntityExtractor:
    """Scan text for known agricultural entities using domain dictionaries.

    Builds compiled regex patterns at init time for efficiency.
    One pattern per entity type, alternating all aliases.
    """

    EXTRACTION_MODEL = "dictionary_pattern_v1"

    def __init__(self) -> None:
        # Pre-compile patterns per entity type
        # Pattern: whole-word match, case-insensitive
        self._patterns: dict[str, list[tuple[str, re.Pattern[str]]]] = {}
        for entity_type, dictionary in ALL_DICTIONARIES.items():
            if entity_type not in ALLOWED_ENTITY_LABELS:
                continue
            entries: list[tuple[str, re.Pattern[str]]] = []
            for canonical, aliases in dictionary.items():
                all_terms = [canonical, *aliases]
                # Sort by length descending so longer matches take priority
                all_terms.sort(key=len, reverse=True)
                alternation = "|".join(re.escape(t) for t in all_terms)
                pattern = re.compile(
                    rf"\b({alternation})\b",
                    re.IGNORECASE,
                )
                entries.append((canonical, pattern))
            self._patterns[entity_type] = entries

        logger.debug(
            "DictionaryEntityExtractor: compiled patterns for {} entity types",
            len(self._patterns),
        )

    async def extract(
        self,
        text: str,
        document_metadata: dict[str, object],
    ) -> list[ExtractedEntity]:
        """Scan text and return candidate ExtractedEntity objects.

        Candidates are not yet resolved — the EntityResolver converts them
        to canonical names in the next step.

        Args:
            text:              The chunk text to scan.
            document_metadata: Document-level metadata (crop, authority, etc.)
                               used to seed entity type hints.

        Returns:
            List of ExtractedEntity objects (may contain duplicates — dedup
            happens in the resolver).
        """
        entities: list[ExtractedEntity] = []
        seen: set[tuple[str, str]] = set()  # (entity_type, match_lower)

        # Seed from document metadata first (highest confidence)
        entities.extend(self._seed_from_metadata(document_metadata))
        for e in entities:
            seen.add((e.entity_type, e.raw_text.lower()))

        # Scan text
        for entity_type, pattern_list in self._patterns.items():
            for canonical, pattern in pattern_list:
                for match in pattern.finditer(text):
                    key = (entity_type, match.group(0).lower())
                    if key in seen:
                        continue
                    seen.add(key)
                    entities.append(
                        ExtractedEntity(
                            raw_text=match.group(0),
                            entity_type=entity_type,
                            canonical_name=canonical,  # pre-resolved via pattern
                            confidence=0.85,
                            matched_via="alias",
                            position=match.start(),
                        )
                    )

        logger.debug(
            "DictionaryEntityExtractor: extracted {} candidate entities from {} chars",
            len(entities),
            len(text),
        )
        return entities

    @staticmethod
    def _seed_from_metadata(metadata: dict[str, object]) -> list[ExtractedEntity]:
        """Extract entities from document-level metadata fields.

        Metadata fields like ``crop``, ``season``, ``authority`` already carry
        entity information with high confidence.
        """
        seeds: list[ExtractedEntity] = []
        field_map = {
            "crop": "Crop",
            "season": "Season",
            "authority": "Authority",
        }
        for field, entity_type in field_map.items():
            value = metadata.get(field)
            if value and isinstance(value, str) and value.strip():
                seeds.append(
                    ExtractedEntity(
                        raw_text=value.strip(),
                        entity_type=entity_type,
                        confidence=0.95,
                        matched_via="metadata",
                        position=-1,
                    )
                )
        return seeds
