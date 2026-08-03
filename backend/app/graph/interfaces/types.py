"""Core data types for the KrishiOS knowledge graph layer.

These are pure Python dataclasses — no Neo4j driver types leak out.
All graph operations return these types, keeping business logic
independent of the underlying graph database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GraphNode:
    """A node in the agricultural knowledge graph.

    Every node has a stable ``node_id`` (UUID string) and a ``label``
    that corresponds to a controlled entity type from the ontology.
    Properties carry the full node payload including canonical_name,
    aliases, and any entity-specific fields.
    """

    node_id: str
    label: str                          # e.g. "Crop", "Disease"
    canonical_name: str
    properties: dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Edge types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EdgeProvenance:
    """Provenance carried on every graph relationship.

    This answers: "Why does KrishiOS believe this relationship?"
    """

    source_document_uuid: str
    source_chunk_id: str
    page_number: int
    authority: str
    confidence: float
    extraction_model: str


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """A typed, provenance-carrying relationship between two nodes."""

    rel_id: str
    from_node_id: str
    to_node_id: str
    rel_type: str                       # Must be in ALLOWED_RELATIONSHIPS
    properties: dict[str, object] = field(default_factory=dict)
    provenance: EdgeProvenance | None = None


# ---------------------------------------------------------------------------
# Path types (for explainable traversal)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GraphPath:
    """An ordered sequence of nodes and edges representing a traversal path.

    This is the explainable unit returned by graph retrieval.

    Example:
        nodes      = [Paddy, Blast, Leaf Lesions]
        edges      = [HAS_DISEASE, HAS_SYMPTOM]
        path_text  = "Paddy → HAS_DISEASE → Blast → HAS_SYMPTOM → Leaf Lesions"
    """

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    relevance_score: float = 0.0

    @property
    def path_text(self) -> str:
        """Return a human-readable representation of the path."""
        if not self.nodes:
            return ""
        parts: list[str] = [self.nodes[0].canonical_name]
        for edge, node in zip(self.edges, self.nodes[1:]):
            parts.append(f"→ {edge.rel_type} →")
            parts.append(node.canonical_name)
        return " ".join(parts)

    @property
    def provenance_list(self) -> list[EdgeProvenance]:
        """Return all provenance records from the path edges."""
        return [e.provenance for e in self.edges if e.provenance is not None]


# ---------------------------------------------------------------------------
# Retrieval result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GraphRetrievalResult:
    """Output of a graph retrieval operation."""

    query: str
    paths: list[GraphPath]
    entities: list[GraphNode]
    latency_ms: float


# ---------------------------------------------------------------------------
# Knowledge status
# ---------------------------------------------------------------------------

# These mirror the status values used as Neo4j node/edge properties.
GRAPH_STATUS_ACTIVE = "ACTIVE"
GRAPH_STATUS_SUPERSEDED = "SUPERSEDED"
GRAPH_STATUS_DRAFT = "DRAFT"
GRAPH_STATUS_REVIEW_REQUIRED = "REVIEW_REQUIRED"
GRAPH_STATUS_REJECTED = "REJECTED"
GRAPH_STATUS_EXPIRED = "EXPIRED"
