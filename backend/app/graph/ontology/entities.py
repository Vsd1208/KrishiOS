"""Controlled entity type definitions for the KrishiOS agricultural ontology.

Why a controlled ontology?
  Uncontrolled entity extraction produces garbage: "paddy crop", "rice plant",
  "Oryza sativa" as three unrelated nodes. A controlled set of labels plus
  entity-specific required properties prevents this at the schema level.

MVP entity types (11 types sufficient for the initial retrieval use-cases):
  Crop, Disease, Pest, Symptom, Treatment, Nutrient,
  SoilType, Season, Advisory, Document, Authority

Deferred: Fertilizer (→ Treatment), WeatherCondition, GovernmentScheme.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Entity labels — the only allowed Neo4j node labels in this system
# ---------------------------------------------------------------------------

ENTITY_CROP = "Crop"
ENTITY_DISEASE = "Disease"
ENTITY_PEST = "Pest"
ENTITY_SYMPTOM = "Symptom"
ENTITY_TREATMENT = "Treatment"
ENTITY_NUTRIENT = "Nutrient"
ENTITY_SOIL_TYPE = "SoilType"
ENTITY_SEASON = "Season"
ENTITY_ADVISORY = "Advisory"
ENTITY_DOCUMENT = "Document"
ENTITY_AUTHORITY = "Authority"

ALLOWED_ENTITY_LABELS: frozenset[str] = frozenset(
    {
        ENTITY_CROP,
        ENTITY_DISEASE,
        ENTITY_PEST,
        ENTITY_SYMPTOM,
        ENTITY_TREATMENT,
        ENTITY_NUTRIENT,
        ENTITY_SOIL_TYPE,
        ENTITY_SEASON,
        ENTITY_ADVISORY,
        ENTITY_DOCUMENT,
        ENTITY_AUTHORITY,
    }
)

# ---------------------------------------------------------------------------
# Required properties per entity type
# Validation checks these before insertion.
# ---------------------------------------------------------------------------

REQUIRED_PROPERTIES: dict[str, list[str]] = {
    ENTITY_CROP: ["canonical_name", "node_id"],
    ENTITY_DISEASE: ["canonical_name", "node_id"],
    ENTITY_PEST: ["canonical_name", "node_id"],
    ENTITY_SYMPTOM: ["canonical_name", "node_id"],
    ENTITY_TREATMENT: ["canonical_name", "node_id", "treatment_type"],
    ENTITY_NUTRIENT: ["canonical_name", "node_id"],
    ENTITY_SOIL_TYPE: ["canonical_name", "node_id"],
    ENTITY_SEASON: ["canonical_name", "node_id"],
    ENTITY_ADVISORY: ["canonical_name", "node_id", "advisory_type"],
    ENTITY_DOCUMENT: ["canonical_name", "node_id", "document_uuid"],
    ENTITY_AUTHORITY: ["canonical_name", "node_id"],
}

# ---------------------------------------------------------------------------
# Disease subtypes — used to validate disease_type property
# ---------------------------------------------------------------------------

DISEASE_TYPES: frozenset[str] = frozenset(
    {"fungal", "bacterial", "viral", "nematode", "deficiency", "abiotic", "unknown"}
)

# ---------------------------------------------------------------------------
# Treatment subtypes
# ---------------------------------------------------------------------------

TREATMENT_TYPES: frozenset[str] = frozenset(
    {"chemical", "biological", "cultural", "mechanical", "unknown"}
)

# ---------------------------------------------------------------------------
# Season values — match the existing PostgreSQL season field convention
# ---------------------------------------------------------------------------

SEASON_VALUES: frozenset[str] = frozenset(
    {"kharif", "rabi", "zaid", "perennial"}
)

# ---------------------------------------------------------------------------
# Advisory subtypes
# ---------------------------------------------------------------------------

ADVISORY_TYPES: frozenset[str] = frozenset(
    {"disease_management", "pest_management", "nutrition", "general", "irrigation", "harvest"}
)
