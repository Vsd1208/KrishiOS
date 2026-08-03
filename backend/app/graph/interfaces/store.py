"""GraphStore Protocol — the abstraction boundary between business logic and Neo4j.

Business logic throughout the graph module talks to ``GraphStore``.
The concrete implementation ``Neo4jGraphStore`` lives in ``graph/store/``.
Tests can substitute a fake store without touching Neo4j.

Design decisions:
  - All operations are async (Neo4j driver supports asyncio).
  - The interface intentionally does NOT expose Cypher.
  - Parameterized operations prevent injection and limit what agents can do.
"""

from __future__ import annotations

from typing import Protocol

from app.graph.interfaces.types import GraphEdge, GraphNode, GraphPath


class GraphStore(Protocol):
    """Contract for graph database operations in KrishiOS.

    Methods are grouped into three concerns:
      1. Node management
      2. Relationship management
      3. Traversal / retrieval
    """

    # ── Node management ───────────────────────────────────────────────────────

    async def upsert_node(
        self,
        label: str,
        node_id: str,
        properties: dict[str, object],
    ) -> GraphNode:
        """Insert or update a node.

        If a node with the given ``node_id`` already exists its properties
        are merged (existing keys not in ``properties`` are preserved).
        """

    async def get_node(self, node_id: str) -> GraphNode | None:
        """Retrieve a single node by its stable UUID."""

    async def find_nodes_by_name(
        self,
        label: str,
        name: str,
        *,
        fuzzy: bool = False,
    ) -> list[GraphNode]:
        """Find nodes matching a canonical name or alias.

        When ``fuzzy=True`` the implementation may use APOC similarity
        or a CONTAINS clause. Default is exact match (case-insensitive).
        """

    # ── Relationship management ───────────────────────────────────────────────

    async def create_relationship(
        self,
        from_node_id: str,
        rel_type: str,
        to_node_id: str,
        properties: dict[str, object],
    ) -> GraphEdge:
        """Create a new relationship with provenance properties.

        Does NOT upsert. A new relationship with its own ``rel_id`` is
        created every time. Callers are responsible for checking for
        duplicates before calling this method.
        """

    async def get_relationship(self, rel_id: str) -> GraphEdge | None:
        """Retrieve a relationship by its stable UUID."""

    async def find_relationships(
        self,
        from_node_id: str,
        rel_type: str | None = None,
        status: str = "ACTIVE",
    ) -> list[GraphEdge]:
        """Return relationships originating from a node, optionally filtered by type."""

    async def deprecate_relationship(
        self,
        rel_id: str,
        superseded_by_id: str | None,
        reason: str,
    ) -> None:
        """Mark a relationship as SUPERSEDED without deleting it.

        Agricultural knowledge is never silently deleted.
        The old relationship remains queryable with status=SUPERSEDED.
        """

    # ── Traversal / retrieval ─────────────────────────────────────────────────

    async def get_neighbors(
        self,
        node_id: str,
        rel_type: str | None = None,
        direction: str = "OUTGOING",
        depth: int = 1,
        status: str = "ACTIVE",
    ) -> list[GraphNode]:
        """Return neighboring nodes within ``depth`` hops.

        Args:
            node_id:   Starting node UUID.
            rel_type:  Optional relationship type filter.
            direction: "OUTGOING", "INCOMING", or "BOTH".
            depth:     Maximum traversal depth (1 = direct neighbors only).
            status:    Edge status filter (default: only ACTIVE edges).
        """

    async def find_paths(
        self,
        from_node_id: str,
        to_label: str,
        rel_types: list[str] | None = None,
        max_hops: int = 3,
        status: str = "ACTIVE",
    ) -> list[GraphPath]:
        """Find all paths from a node to any node of ``to_label``.

        Used for traversal queries like:
          "What diseases does Paddy have, and what symptoms do those diseases have?"
        """

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def close(self) -> None:
        """Release driver resources."""

    async def verify_connectivity(self) -> bool:
        """Return True if the graph database is reachable."""
