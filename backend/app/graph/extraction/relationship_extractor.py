"""Pattern-based relationship extractor for the KrishiOS knowledge graph.

MVP approach: syntactic patterns are mapped to controlled predicates.
The extractor finds pairs of resolved entities in the same sentence/chunk
and checks if they match a known relationship pattern.

Example:
  Text: "Paddy is susceptible to Blast disease."
  Entities: "Paddy" (Crop), "Blast" (Disease)
  Pattern: "<Crop>.*susceptible to.*<Disease>" → HAS_DISEASE

Only relationships defined in the ontology are emitted.
"""

from __future__ import annotations

import re
from typing import Protocol

from loguru import logger

from app.graph.extraction.types import ExtractedRelationship, ResolvedEntity
from app.graph.ontology.relationships import is_allowed_triple


class RelationshipExtractorProtocol(Protocol):
    """Contract for relationship extractors."""

    async def extract(
        self,
        entities: list[ResolvedEntity],
        text: str,
        document_metadata: dict[str, object],
    ) -> list[ExtractedRelationship]:
        """Extract candidate relationships between resolved entities."""


class PatternRelationshipExtractor:
    """Extract relationships using syntactic patterns and co-occurrence.

    Uses a simple sliding window or sentence-level co-occurrence plus
    keyword matching.
    """

    EXTRACTION_MODEL = "pattern_extractor_v1"

    def __init__(self) -> None:
        # Define basic keyword triggers for relationship types
        self._triggers = {
            "HAS_DISEASE": ["susceptible to", "infected by", "suffers from", "affected by", "disease"],
            "HAS_SYMPTOM": ["causes", "shows", "symptoms include", "manifests as", "characterized by", "leads to"],
            "AFFECTS": ["attacks", "damages", "infests", "feeds on", "affects"],
            "TREATED_BY": ["treated with", "controlled by", "managed using", "spray", "apply", "treatment"],
            "REQUIRES_NUTRIENT": ["requires", "needs", "responds to", "deficient in"],
            "SUITABLE_FOR": ["grown in", "suitable for", "prefers", "best in", "thrives in"],
            "GROWN_IN": ["cultivated in", "grown during", "sown in", "season"],
        }

    async def extract(
        self,
        entities: list[ResolvedEntity],
        text: str,
        document_metadata: dict[str, object],
    ) -> list[ExtractedRelationship]:
        """Extract relationships from text and metadata."""
        relationships: list[ExtractedRelationship] = []
        
        # 1. Metadata-inferred relationships (high confidence)
        # e.g. Document -> Mentions -> Crop
        relationships.extend(self._extract_from_metadata(entities, document_metadata))

        # 2. Text co-occurrence (sentences)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Find entities in this sentence
            sentence_entities = [
                e for e in entities 
                if e.input_string.lower() in sentence_lower
                and e.matched_via != "metadata"
            ]
            
            # Check all pairs in the sentence
            for i, subj in enumerate(sentence_entities):
                for obj in sentence_entities[i+1:]:
                    # Skip self-links
                    if subj.canonical_name == obj.canonical_name:
                        continue
                        
                    # Try subj -> obj
                    rel_type = self._infer_relationship(subj, obj, sentence_lower)
                    if rel_type and is_allowed_triple(subj.entity_type, rel_type, obj.entity_type):
                        relationships.append(self._create_rel(subj, rel_type, obj, sentence))
                        
                    # Try obj -> subj
                    rel_type = self._infer_relationship(obj, subj, sentence_lower)
                    if rel_type and is_allowed_triple(obj.entity_type, rel_type, subj.entity_type):
                        relationships.append(self._create_rel(obj, rel_type, subj, sentence))

        logger.debug("PatternRelationshipExtractor: extracted {} relationships", len(relationships))
        return relationships

    def _infer_relationship(self, subj: ResolvedEntity, obj: ResolvedEntity, sentence_lower: str) -> str | None:
        """Infer relationship type based on entity types and keywords."""
        # Simple rule: if entity types map to exactly one allowed relationship, use it if they co-occur.
        # But to be safer, we check for trigger words.
        
        # Determine possible relationships based on ontology
        possible = []
        for rel_type, triggers in self._triggers.items():
            if is_allowed_triple(subj.entity_type, rel_type, obj.entity_type):
                possible.append(rel_type)
                
        if not possible:
            return None
            
        # If there's only one possibility, we might just assume it from co-occurrence (confidence 0.5)
        # If we find trigger words, confidence is higher.
        for rel_type in possible:
            for trigger in self._triggers.get(rel_type, []):
                if trigger in sentence_lower:
                    return rel_type # Found strong evidence
                    
        # Fallback: if only one valid relationship exists in ontology for this pair, assume it.
        # Example: Crop and Disease co-occurring -> Crop HAS_DISEASE Disease
        if len(possible) == 1:
            return possible[0]
            
        return None

    def _create_rel(self, subj: ResolvedEntity, rel_type: str, obj: ResolvedEntity, sentence: str) -> ExtractedRelationship:
        return ExtractedRelationship(
            subject=subj,
            predicate=rel_type,
            obj=obj,
            confidence=0.7, # Base confidence for pattern matching
            source_text=sentence.strip(),
            source_chunk_id="", # Filled later by ingestion pipeline
            document_uuid="",   # Filled later
            page_number=0,      # Filled later
            authority="",       # Filled later
            extraction_model=self.EXTRACTION_MODEL,
        )

    def _extract_from_metadata(self, entities: list[ResolvedEntity], metadata: dict[str, object]) -> list[ExtractedRelationship]:
        """Extract implied relationships from document metadata.
        
        Example: Document PUBLISHED_BY Authority.
        """
        rels = []
        doc_uuid = str(metadata.get("document_uuid", ""))
        
        # If we had a Document entity, we could link it here.
        # For MVP, we mainly focus on domain entities.
        
        return rels
