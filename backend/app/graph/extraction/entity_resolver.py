"""Entity resolver — maps raw text to canonical ontology entities.

Purpose:
  Before any entity enters the knowledge graph, it must be resolved
  to a canonical name. This prevents entity fragmentation:
    "rice", "Rice crop", "paddy crop" → canonical = "Paddy"

Resolution strategy (in order):
  1. Exact match on canonical_name (case-insensitive)
  2. Alias match from domain dictionaries
  3. Substring containment (partial match, lower confidence)

Design:
  The resolver is instantiated once and its lookup tables are built
  from the domain dictionaries at init time. This avoids scanning
  dictionaries on every call.
"""

from __future__ import annotations

import re

from app.graph.extraction.types import ExtractedEntity, ResolvedEntity
from app.graph.ontology.dictionaries import ALL_DICTIONARIES, build_reverse_lookup


class EntityResolver:
    """Resolves raw text spans to canonical entity names.

    The resolver builds reverse lookup tables at init time:
      alias_lowercase → canonical_name, per entity_type.

    Resolution confidence:
      - Exact canonical match:  0.95
      - Alias match:            0.85
      - Substring match:        0.65
      - No match:               0.0 (returns None)
    """

    def __init__(self) -> None:
        # Build per-type lookup once
        self._lookups: dict[str, dict[str, str]] = {
            entity_type: build_reverse_lookup(entity_type)
            for entity_type in ALL_DICTIONARIES
        }

    def resolve(self, entity: ExtractedEntity) -> ResolvedEntity | None:
        """Attempt to resolve an extracted entity to a canonical name.

        Returns None if no match is found with confidence above 0.
        """
        raw = entity.raw_text.strip()
        normalized = self._normalize(raw)
        entity_type = entity.entity_type
        lookup = self._lookups.get(entity_type, {})

        # --- Pass 1: exact match ---
        if normalized in lookup:
            canonical = lookup[normalized]
            return ResolvedEntity(
                canonical_name=canonical,
                entity_type=entity_type,
                confidence=0.95,
                input_string=raw,
                matched_via="exact",
                aliases=self._aliases_for(entity_type, canonical),
            )

        # --- Pass 2: token substring match ---
        # e.g. "yellow leaf rice" should match "Paddy" via "rice"
        tokens = normalized.split()
        for token in tokens:
            if token in lookup:
                canonical = lookup[token]
                return ResolvedEntity(
                    canonical_name=canonical,
                    entity_type=entity_type,
                    confidence=0.75,
                    input_string=raw,
                    matched_via="token",
                    aliases=self._aliases_for(entity_type, canonical),
                )

        # --- Pass 3: containment in lookup keys ---
        for alias, canonical in lookup.items():
            if alias in normalized or normalized in alias:
                return ResolvedEntity(
                    canonical_name=canonical,
                    entity_type=entity_type,
                    confidence=0.60,
                    input_string=raw,
                    matched_via="substring",
                    aliases=self._aliases_for(entity_type, canonical),
                )

        return None

    def resolve_bulk(self, entities: list[ExtractedEntity]) -> list[ResolvedEntity]:
        """Resolve a list of extracted entities, dropping unresolved ones."""
        resolved = []
        for entity in entities:
            result = self.resolve(entity)
            if result is not None:
                resolved.append(result)
        return resolved

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _normalize(text: str) -> str:
        """Lowercase, remove punctuation, collapse whitespace."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _aliases_for(self, entity_type: str, canonical_name: str) -> list[str]:
        """Return the alias list for a canonical name from the dictionary."""
        dictionary = ALL_DICTIONARIES.get(entity_type, {})
        return dictionary.get(canonical_name, [])
