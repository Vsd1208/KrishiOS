"""Validates extracted relationships before they enter the knowledge graph.

Enforces ontology rules:
- Known entity types
- Allowed relationship predicates
- Correct (subject, predicate, object) type triples
- Self-link prevention
"""

from __future__ import annotations

from loguru import logger

from app.graph.extraction.types import ExtractedRelationship
from app.graph.ontology.entities import ALLOWED_ENTITY_LABELS
from app.graph.ontology.relationships import is_allowed_triple


class RelationshipValidator:
    """Validates candidate relationships against the agricultural ontology."""

    def validate(self, relationships: list[ExtractedRelationship]) -> list[ExtractedRelationship]:
        """Filter out invalid relationships.

        Returns only relationships that pass all ontology checks.
        Logs warnings for rejected relationships to help tune extractors.
        """
        valid = []
        for rel in relationships:
            if self._is_valid(rel):
                valid.append(rel)
        return valid

    def _is_valid(self, rel: ExtractedRelationship) -> bool:
        # 1. No self-links
        if rel.subject.canonical_name == rel.obj.canonical_name and rel.subject.entity_type == rel.obj.entity_type:
            logger.debug(
                "RelationshipValidator: Rejected self-link {} -> {}", 
                rel.subject.canonical_name, 
                rel.obj.canonical_name
            )
            return False

        # 2. Known entity types
        if rel.subject.entity_type not in ALLOWED_ENTITY_LABELS:
            logger.debug("RelationshipValidator: Rejected unknown subject type '{}'", rel.subject.entity_type)
            return False
            
        if rel.obj.entity_type not in ALLOWED_ENTITY_LABELS:
            logger.debug("RelationshipValidator: Rejected unknown object type '{}'", rel.obj.entity_type)
            return False

        # 3. Allowed ontology triple
        if not is_allowed_triple(rel.subject.entity_type, rel.predicate, rel.obj.entity_type):
            logger.debug(
                "RelationshipValidator: Rejected triple ({} -[{}]-> {})",
                rel.subject.entity_type,
                rel.predicate,
                rel.obj.entity_type
            )
            return False

        return True
