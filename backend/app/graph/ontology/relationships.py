"""Controlled relationship type definitions for the KrishiOS agricultural ontology.

Why controlled predicates?
  Without a fixed vocabulary, extractors produce arbitrary strings like
  "is treated by", "can be treated with", "treated using" — all meaning
  the same thing but creating three different relationship types. This
  makes traversal and querying unreliable.

  Every relationship the extractor attempts to create must appear in
  ALLOWED_RELATIONSHIPS. The validator rejects anything else.

Each entry defines:
  - The relationship type string (used in Cypher)
  - Allowed (from_label, to_label) pairs for validation
"""

from __future__ import annotations

from app.graph.ontology.entities import (
    ENTITY_ADVISORY,
    ENTITY_AUTHORITY,
    ENTITY_CROP,
    ENTITY_DISEASE,
    ENTITY_DOCUMENT,
    ENTITY_NUTRIENT,
    ENTITY_PEST,
    ENTITY_SEASON,
    ENTITY_SOIL_TYPE,
    ENTITY_SYMPTOM,
    ENTITY_TREATMENT,
)

# ---------------------------------------------------------------------------
# Relationship type constants
# ---------------------------------------------------------------------------

REL_HAS_DISEASE = "HAS_DISEASE"
REL_HAS_SYMPTOM = "HAS_SYMPTOM"
REL_AFFECTS = "AFFECTS"
REL_TREATED_BY = "TREATED_BY"
REL_REQUIRES_NUTRIENT = "REQUIRES_NUTRIENT"
REL_SUITABLE_FOR = "SUITABLE_FOR"
REL_GROWN_IN = "GROWN_IN"
REL_APPLIES_TO = "APPLIES_TO"
REL_RECOMMENDS = "RECOMMENDS"
REL_PUBLISHED_BY = "PUBLISHED_BY"
REL_SUPPORTS = "SUPPORTS"
REL_MENTIONS = "MENTIONS"
REL_SUPERSEDES = "SUPERSEDES"

# ---------------------------------------------------------------------------
# Allowed (from_label, rel_type, to_label) triples.
# The validator checks each candidate relationship against this set.
# ---------------------------------------------------------------------------

# Each entry: (from_label, rel_type, to_label)
ALLOWED_TRIPLES: frozenset[tuple[str, str, str]] = frozenset(
    {
        # Crop relationships
        (ENTITY_CROP, REL_HAS_DISEASE, ENTITY_DISEASE),
        (ENTITY_CROP, REL_REQUIRES_NUTRIENT, ENTITY_NUTRIENT),
        (ENTITY_CROP, REL_SUITABLE_FOR, ENTITY_SOIL_TYPE),
        (ENTITY_CROP, REL_GROWN_IN, ENTITY_SEASON),
        # Disease relationships
        (ENTITY_DISEASE, REL_HAS_SYMPTOM, ENTITY_SYMPTOM),
        (ENTITY_DISEASE, REL_TREATED_BY, ENTITY_TREATMENT),
        # Pest relationships
        (ENTITY_PEST, REL_AFFECTS, ENTITY_CROP),
        (ENTITY_PEST, REL_TREATED_BY, ENTITY_TREATMENT),
        # Nutrient-deficiency symptoms
        (ENTITY_NUTRIENT, REL_HAS_SYMPTOM, ENTITY_SYMPTOM),
        # Advisory relationships
        (ENTITY_ADVISORY, REL_APPLIES_TO, ENTITY_CROP),
        (ENTITY_ADVISORY, REL_RECOMMENDS, ENTITY_TREATMENT),
        (ENTITY_ADVISORY, REL_SUPERSEDES, ENTITY_ADVISORY),
        # Document provenance relationships
        (ENTITY_DOCUMENT, REL_PUBLISHED_BY, ENTITY_AUTHORITY),
        (ENTITY_DOCUMENT, REL_SUPPORTS, ENTITY_ADVISORY),
        (ENTITY_DOCUMENT, REL_MENTIONS, ENTITY_CROP),
    }
)

ALLOWED_RELATIONSHIPS: frozenset[str] = frozenset(
    {triple[1] for triple in ALLOWED_TRIPLES}
)


def is_allowed_triple(from_label: str, rel_type: str, to_label: str) -> bool:
    """Return True if this (from_label, rel_type, to_label) triple is in the ontology."""
    return (from_label, rel_type, to_label) in ALLOWED_TRIPLES


def get_allowed_targets(from_label: str, rel_type: str) -> list[str]:
    """Return the allowed target labels for a given (from_label, rel_type) pair."""
    return [
        to_label
        for (fl, rt, to_label) in ALLOWED_TRIPLES
        if fl == from_label and rt == rel_type
    ]
