"""Agricultural language normalizer mapping regional and code-switched terms to canonical entities."""

from dataclasses import dataclass, field
import re
from loguru import logger

from app.graph.extraction.entity_resolver import EntityResolver
from app.graph.extraction.types import ExtractedEntity


@dataclass(frozen=True, slots=True)
class NormalizedQueryResult:
    raw_query: str
    normalized_query: str
    detected_language: str
    is_code_switched: bool
    resolved_crop: str | None
    resolved_disease: str | None
    resolved_symptom: str | None
    extracted_entities: list[dict[str, Any]] = field(default_factory=list)


class AgriculturalLanguageNormalizer:
    """Normalizes regional (Telugu, Hindi) and code-switched agricultural queries to canonical terms."""

    # Direct mapping dictionary for quick regional term resolution
    REGIONAL_TERM_MAP: dict[str, tuple[str, str]] = {
        # (term_lowercase): (canonical_name, entity_type)
        "వరి": ("Paddy", "Crop"),
        "వరి పైరు": ("Paddy", "Crop"),
        "వరి crop": ("Paddy", "Crop"),
        "dhaan": ("Paddy", "Crop"),
        "धान": ("Paddy", "Crop"),
        "धान की फसल": ("Paddy", "Crop"),
        "chawal": ("Paddy", "Crop"),
        "kapas": ("Cotton", "Crop"),
        "కపాస్": ("Cotton", "Crop"),
        "tamatar": ("Tomato", "Crop"),
        "టమాట": ("Tomato", "Crop"),
        "gehun": ("Wheat", "Crop"),
        "గోధుమ": ("Wheat", "Crop"),

        # Disease / Pest terms
        "అగ్గి తెగులు": ("Blast", "Disease"),
        "భూరా धब्बा": ("Brown Spot", "Disease"),
        "भूरा धब्बा": ("Brown Spot", "Disease"),
        "yellow spots": ("Yellow Leaves", "Symptom"),
        "పసుపుగ": ("Yellow Leaves", "Symptom"),
        "పసుపుగా": ("Yellow Leaves", "Symptom"),
        "పీలే ధब्बे": ("Yellow Leaves", "Symptom"),
    }

    def __init__(self, entity_resolver: EntityResolver | None = None) -> None:
        self._entity_resolver = entity_resolver or EntityResolver()

    def normalize(self, query: str, language: str) -> NormalizedQueryResult:
        """Process raw speech transcript, extract & resolve entities, and return normalized representation."""
        clean_q = query.strip()
        q_lower = clean_q.lower()

        extracted: list[dict[str, Any]] = []
        resolved_crop: str | None = None
        resolved_disease: str | None = None
        resolved_symptom: str | None = None
        is_code_switched = False

        # Check for Latin characters mixed with Non-Latin or English keywords in regional queries
        has_latin = bool(re.search(r"[a-zA-Z]", clean_q))
        has_non_latin = bool(re.search(r"[\u0C00-\u0C7F\u0900-\u097F]", clean_q))
        if has_latin and has_non_latin:
            is_code_switched = True

        # Pass 1: Check direct regional term map
        for term, (canonical, etype) in self.REGIONAL_TERM_MAP.items():
            if term.lower() in q_lower or term in clean_q:
                extracted.append({
                    "raw_span": term,
                    "canonical_name": canonical,
                    "entity_type": etype,
                    "confidence": 0.95,
                })
                if etype == "Crop" and not resolved_crop:
                    resolved_crop = canonical
                elif etype == "Disease" and not resolved_disease:
                    resolved_disease = canonical
                elif etype == "Symptom" and not resolved_symptom:
                    resolved_symptom = canonical

        # Pass 2: Fallback to Sprint 6 EntityResolver
        for token in clean_q.split():
            ext_entity = ExtractedEntity(raw_text=token, entity_type="Crop", confidence=0.8)
            resolved = self._entity_resolver.resolve(ext_entity)
            if resolved:
                if not resolved_crop:
                    resolved_crop = resolved.canonical_name
                extracted.append({
                    "raw_span": token,
                    "canonical_name": resolved.canonical_name,
                    "entity_type": "Crop",
                    "confidence": resolved.confidence,
                })

        # Build normalized english-like query string for RAG vector search if applicable
        norm_parts = [clean_q]
        if resolved_crop:
            norm_parts.append(f"Crop: {resolved_crop}")
        if resolved_disease:
            norm_parts.append(f"Disease: {resolved_disease}")
        if resolved_symptom:
            norm_parts.append(f"Symptom: {resolved_symptom}")

        normalized_query_str = " | ".join(norm_parts)

        return NormalizedQueryResult(
            raw_query=clean_q,
            normalized_query=normalized_query_str,
            detected_language=language,
            is_code_switched=is_code_switched,
            resolved_crop=resolved_crop,
            resolved_disease=resolved_disease,
            resolved_symptom=resolved_symptom,
            extracted_entities=extracted,
        )
