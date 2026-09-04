"""Neo4j implementation of the GraphStore protocol.

Design decisions:
  - Uses the official ``neo4j`` async driver (AsyncGraphDatabase).
  - All Cypher queries are parameterized. No string interpolation for values.
  - The application never exposes raw Cypher to callers or agents.
  - Nodes are matched by ``node_id`` (UUID) for all updates.
  - Relationships carry ``rel_id`` (UUID) for stable referencing.
  - Semantic relationships are deduplicated by:
        (from_node_id, relationship_type, to_node_id)
  - The database constraint ensuring ``node_id`` uniqueness is created
    on first startup via ``ensure_constraints()``.
  - Status filtering defaults to ACTIVE on all traversal queries.

Error handling:
  - Neo4j driver exceptions are caught and re-raised as plain RuntimeError
    so callers never import Neo4j exception classes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from loguru import logger

try:
    from neo4j import AsyncDriver, AsyncGraphDatabase
    _NEO4J_AVAILABLE = True
except ImportError:  # pragma: no cover
    _NEO4J_AVAILABLE = False
    AsyncDriver = None  # type: ignore[assignment,misc]

from app.graph.interfaces.types import (
    EdgeProvenance,
    GraphEdge,
    GraphNode,
    GraphPath,
    GRAPH_STATUS_ACTIVE,
    GRAPH_STATUS_SUPERSEDED,
)


class Neo4jGraphStore:
    """Concrete GraphStore backed by Neo4j 5 Community Edition.

    Instantiate once per application lifetime (lifespan event).
    Use ``close()`` during shutdown to release driver connections.
    """

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str,
    ) -> None:
        if not _NEO4J_AVAILABLE:
            raise RuntimeError(
                "neo4j package not installed. "
                "Add 'neo4j>=5.18.0' to dependencies."
            )

        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            uri,
            auth=(user, password),
        )
        self._database = database

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Release the driver connection pool."""
        await self._driver.close()
        logger.info("Neo4jGraphStore: driver closed")

    async def verify_connectivity(self) -> bool:
        """Return True if Neo4j is reachable."""
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception as exc:
            logger.warning(
                "Neo4jGraphStore: connectivity check failed: {}",
                exc,
            )
            return False

    async def ensure_constraints(self) -> None:
        """Create uniqueness constraints and indexes required by the ontology.

        Safe to call multiple times.
        Called once during application startup.
        """
        node_labels = [
            "Crop",
            "Disease",
            "Pest",
            "Symptom",
            "Treatment",
            "Nutrient",
            "SoilType",
            "Season",
            "Advisory",
            "Document",
            "Authority",
        ]

        async with self._driver.session(
            database=self._database
        ) as session:
            for label in node_labels:
                # Uniqueness on node_id
                await session.run(
                    f"CREATE CONSTRAINT {label.lower()}_node_id_unique "
                    "IF NOT EXISTS "
                    f"FOR (n:{label}) REQUIRE n.node_id IS UNIQUE"
                )

                # Index on canonical_name for fast lookup
                await session.run(
                    f"CREATE INDEX {label.lower()}_canonical_name "
                    "IF NOT EXISTS "
                    f"FOR (n:{label}) ON (n.canonical_name)"
                )

        logger.info(
            "Neo4jGraphStore: constraints and indexes verified"
        )

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    async def upsert_node(
        self,
        label: str,
        node_id: str,
        properties: dict[str, object],
    ) -> GraphNode:
        """Insert or update a node by node_id.

        MERGE matches on node_id.
        ON CREATE sets all properties.
        ON MATCH updates mutable fields.
        """
        now = datetime.now(UTC).isoformat()

        props = {
            **properties,
            "node_id": node_id,
            "updated_at": now,
            "ontology_version": "v1",
        }

        create_props = {
            **props,
            "created_at": now,
        }

        query = (
            f"MERGE (n:{label} {{node_id: $node_id}})\n"
            "ON CREATE SET n = $create_props\n"
            "ON MATCH SET n += $match_props\n"
            "RETURN n"
        )

        match_props = {
            key: value
            for key, value in props.items()
            if key != "node_id"
        }

        try:
            async with self._driver.session(
                database=self._database
            ) as session:
                result = await session.run(
                    query,
                    node_id=node_id,
                    create_props=create_props,
                    match_props=match_props,
                )

                record = await result.single()

                if record is None:
                    raise RuntimeError(
                        f"Failed to upsert node: {label}/{node_id}"
                    )

                return self._node_from_record(
                    record["n"],
                    label,
                )

        except Exception as exc:
            raise RuntimeError(
                f"upsert_node failed for {label}/{node_id}: {exc}"
            ) from exc

    async def get_node(
        self,
        node_id: str,
    ) -> GraphNode | None:
        """Retrieve a node by stable UUID."""
        query = (
            "MATCH (n {node_id: $node_id}) "
            "RETURN n, labels(n) AS labels "
            "LIMIT 1"
        )

        try:
            async with self._driver.session(
                database=self._database
            ) as session:
                result = await session.run(
                    query,
                    node_id=node_id,
                )

                record = await result.single()

                if record is None:
                    return None

                label = (
                    record["labels"][0]
                    if record["labels"]
                    else "Unknown"
                )

                return self._node_from_record(
                    record["n"],
                    label,
                )

        except Exception as exc:
            raise RuntimeError(
                f"get_node failed for {node_id}: {exc}"
            ) from exc

    async def find_nodes_by_name(
        self,
        label: str,
        name: str,
        *,
        fuzzy: bool = False,
    ) -> list[GraphNode]:
        """Find nodes by canonical_name or alias match."""
        if fuzzy:
            query = (
                f"MATCH (n:{label}) "
                "WHERE toLower(n.canonical_name) "
                "CONTAINS toLower($name) "
                "OR any(a IN n.aliases "
                "WHERE toLower(a) CONTAINS toLower($name)) "
                "RETURN n "
                "LIMIT 20"
            )
        else:
            query = (
                f"MATCH (n:{label}) "
                "WHERE toLower(n.canonical_name) = toLower($name) "
                "OR any(a IN n.aliases "
                "WHERE toLower(a) = toLower($name)) "
                "RETURN n "
                "LIMIT 20"
            )

        try:
            async with self._driver.session(
                database=self._database
            ) as session:
                result = await session.run(
                    query,
                    name=name,
                )

                records = await result.data()

                return [
                    self._node_from_record(
                        record["n"],
                        label,
                    )
                    for record in records
                ]

        except Exception as exc:
            raise RuntimeError(
                f"find_nodes_by_name failed: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Relationship management
    # ------------------------------------------------------------------

    async def create_relationship(
        self,
        from_node_id: str,
        rel_type: str,
        to_node_id: str,
        properties: dict[str, object],
    ) -> GraphEdge:
        """Create or reuse an ACTIVE semantic relationship.

        Semantic identity:
            (from_node_id, rel_type, to_node_id)

        Existing ACTIVE relationships are reused. This prevents duplicate
        relationships when multiple extraction candidates represent the
        same knowledge-graph fact.
        """
        now = datetime.now(UTC).isoformat()

        find_query = (
            f"MATCH (a {{node_id: $from_id}})"
            f"-[r:{rel_type}]->"
            f"(b {{node_id: $to_id}}) "
            "WHERE r.status = $active_status "
            "RETURN r"
            " LIMIT 1"
        )

        create_query = (
            "MATCH (a {node_id: $from_id}), "
            "(b {node_id: $to_id}) "
            f"CREATE (a)-[r:{rel_type} $props]->(b) "
            "RETURN r"
        )

        try:
            async with self._driver.session(
                database=self._database
            ) as session:
                # ----------------------------------------------------------
                # 1. Check for an existing ACTIVE semantic relationship
                # ----------------------------------------------------------
                result = await session.run(
                    find_query,
                    from_id=from_node_id,
                    to_id=to_node_id,
                    active_status=GRAPH_STATUS_ACTIVE,
                )

                existing = await result.single()

                if existing is not None:
                    logger.info(
                        "Neo4jGraphStore: reusing existing relationship "
                        "{}-[{}]->{}",
                        from_node_id,
                        rel_type,
                        to_node_id,
                    )

                    return self._edge_from_record(
                        existing["r"],
                        rel_type,
                        from_node_id,
                        to_node_id,
                    )

                # ----------------------------------------------------------
                # 2. No existing relationship -> create one
                # ----------------------------------------------------------
                rel_id = str(uuid.uuid4())

                props = {
                    **properties,
                    "rel_id": rel_id,
                    "created_at": now,
                    "updated_at": now,
                    "status": GRAPH_STATUS_ACTIVE,
                }

                result = await session.run(
                    create_query,
                    from_id=from_node_id,
                    to_id=to_node_id,
                    props=props,
                )

                record = await result.single()
                if record is None:
                    raise RuntimeError(
                        f"Nodes not found: "
                        f"{from_node_id} or {to_node_id}"
                    )

                logger.info(
                    "Neo4jGraphStore: created relationship "
                    "{}-[{}]->{} with rel_id={}",
                    from_node_id,
                    rel_type,
                    to_node_id,
                    rel_id,
                )

                return self._edge_from_record(
                    record["r"],
                    rel_type,
                    from_node_id,
                    to_node_id,
                )

        except Exception as exc:
            raise RuntimeError(
                f"create_relationship failed: {exc}"
            ) from exc

    async def get_relationship(
        self,
        rel_id: str,
    ) -> GraphEdge | None:
        """Retrieve a relationship by its stable rel_id."""
        query = (
            "MATCH (a)-[r {rel_id: $rel_id}]->(b) "
            "RETURN r, "
            "type(r) AS rel_type, "
            "a.node_id AS from_id, "
            "b.node_id AS to_id"
        )

        try:
            async with self._driver.session(
                database=self._database
            ) as session:
                result = await session.run(
                    query,
                    rel_id=rel_id,
                )

                record = await result.single()

                if record is None:
                    return None

                return self._edge_from_record(
                    record["r"],
                    record["rel_type"],
                    record["from_id"],
                    record["to_id"],
                )

        except Exception as exc:
            raise RuntimeError(
                f"get_relationship failed for {rel_id}: {exc}"
            ) from exc

    async def find_relationships(
        self,
        from_node_id: str,
        rel_type: str | None = None,
        status: str = GRAPH_STATUS_ACTIVE,
    ) -> list[GraphEdge]:
        """Return relationships from a node."""
        if rel_type:
            query = (
                f"MATCH (a {{node_id: $from_id}})"
                f"-[r:{rel_type}]->(b) "
                "WHERE r.status = $status "
                "RETURN r, "
                "type(r) AS rel_type, "
                "b.node_id AS to_id"
            )
        else:
            query = (
                "MATCH (a {node_id: $from_id})-[r]->(b) "
                "WHERE r.status = $status "
                "RETURN r, "
                "type(r) AS rel_type, "
                "b.node_id AS to_id"
            )

        try:
            async with self._driver.session(
                database=self._database
            ) as session:
                result = await session.run(
                    query,
                    from_id=from_node_id,
                    status=status,
                )

                records = await result.data()

                return [
                    self._edge_from_record(
                        record["r"],
                        record["rel_type"],
                        from_node_id,
                        record["to_id"],
                    )
                    for record in records
                ]

        except Exception as exc:
            raise RuntimeError(
                f"find_relationships failed: {exc}"
            ) from exc

    async def deprecate_relationship(
        self,
        rel_id: str,
        superseded_by_id: str | None,
        reason: str,
    ) -> None:
        """Mark a relationship SUPERSEDED without deleting it."""
        now = datetime.now(UTC).isoformat()

        query = (
            "MATCH ()-[r {rel_id: $rel_id}]->() "
            "SET r.status = $status, "
            "r.updated_at = $now, "
            "r.deprecation_reason = $reason, "
            "r.superseded_by = $superseded_by"
        )

        try:
            async with self._driver.session(
                database=self._database
            ) as session:
                await session.run(
                    query,
                    rel_id=rel_id,
                    status=GRAPH_STATUS_SUPERSEDED,
                    now=now,
                    reason=reason,
                    superseded_by=superseded_by_id or "",
                )

        except Exception as exc:
            raise RuntimeError(
                f"deprecate_relationship failed: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Traversal / retrieval
    # ------------------------------------------------------------------

    async def get_neighbors(
        self,
        node_id: str,
        rel_type: str | None = None,
        direction: str = "OUTGOING",
        depth: int = 1,
        status: str = GRAPH_STATUS_ACTIVE,
    ) -> list[GraphNode]:
        """Return neighboring nodes within depth hops."""
        if direction == "OUTGOING":
            pattern = f"-[r*1..{depth}]->"
        elif direction == "INCOMING":
            pattern = f"<-[r*1..{depth}]-"
        else:
            pattern = f"-[r*1..{depth}]-"

        # For single-rel-type queries, r is not a list.
        if rel_type and depth == 1:
            query = (
                f"MATCH (a {{node_id: $node_id}})"
                f"-[r:{rel_type}]->(b) "
                "WHERE r.status = $status "
                "RETURN DISTINCT b, labels(b) AS labels"
            )
        else:
            query = (
                f"MATCH (a {{node_id: $node_id}})"
                f"{pattern}(b) "
                "WHERE all("
                "rel IN r WHERE rel.status = $status"
                ") "
                "RETURN DISTINCT b, labels(b) AS labels"
            )

        try:
            async with self._driver.session(
                database=self._database
            ) as session:
                result = await session.run(
                    query,
                    node_id=node_id,
                    status=status,
                )

                records = await result.data()

                return [
                    self._node_from_record(
                        record["b"],
                        record["labels"][0]
                        if record["labels"]
                        else "Unknown",
                    )
                    for record in records
                ]

        except Exception as exc:
            raise RuntimeError(
                f"get_neighbors failed: {exc}"
            ) from exc

    async def find_paths(
        self,
        from_node_id: str,
        to_label: str,
        rel_types: list[str] | None = None,
        max_hops: int = 3,
        status: str = GRAPH_STATUS_ACTIVE,
    ) -> list[GraphPath]:
        """Find all paths from a node to nodes of to_label."""
        query = (
            f"MATCH path = "
            f"(a {{node_id: $from_id}})"
            f"-[r*1..{max_hops}]->"
            f"(b:{to_label}) "
            "WHERE all("
            "rel IN relationships(path) "
            "WHERE rel.status = $status"
            ") "
            "RETURN nodes(path) AS ns, "
            "relationships(path) AS rels, "
            "length(path) AS path_length "
            "ORDER BY path_length ASC "
            "LIMIT 10"
        )

        try:
            async with self._driver.session(
                database=self._database
            ) as session:
                result = await session.run(
                    query,
                    from_id=from_node_id,
                    status=status,
                )

                records = await result.data()

                return [
                    self._path_from_record(record)
                    for record in records
                ]

        except Exception as exc:
            raise RuntimeError(
                f"find_paths failed: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _node_from_record(
        node_data: Any,
        label: str,
    ) -> GraphNode:
        """Convert a Neo4j node object to a GraphNode dataclass."""
        props = dict(node_data)

        return GraphNode(
            node_id=props.get("node_id", ""),
            label=label,
            canonical_name=props.get("canonical_name", ""),
            properties=props,
        )

    @staticmethod
    def _edge_from_record(
        rel_data: Any,
        rel_type: str,
        from_node_id: str,
        to_node_id: str,
    ) -> GraphEdge:
        """Convert a Neo4j relationship object to a GraphEdge dataclass."""
        props = dict(rel_data)

        provenance: EdgeProvenance | None = None

        if "source_document_uuid" in props:
            provenance = EdgeProvenance(
                source_document_uuid=props.get(
                    "source_document_uuid",
                    "",
                ),
                source_chunk_id=props.get(
                    "source_chunk_id",
                    "",
                ),
                page_number=int(
                    props.get("page_number", 0)
                ),
                authority=props.get(
                    "authority",
                    "",
                ),
                confidence=float(
                    props.get("confidence", 0.0)
                ),
                extraction_model=props.get(
                    "extraction_model",
                    "",
                ),
            )

        return GraphEdge(
            rel_id=props.get("rel_id", ""),
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            rel_type=rel_type,
            properties=props,
            provenance=provenance,
        )

    def _path_from_record(
        self,
        record: dict[str, Any],
    ) -> GraphPath:
        """Convert a Neo4j path record to a GraphPath dataclass."""
        ns = record.get("ns", [])
        rels = record.get("rels", [])

        nodes: list[GraphNode] = []

        for i, node_data in enumerate(ns):
            label = "Unknown"

            props = (
                dict(node_data)
                if hasattr(node_data, "items")
                else node_data
            )

            nodes.append(
                GraphNode(
                    node_id=props.get(
                        "node_id",
                        f"unknown_{i}",
                    ),
                    label=label,
                    canonical_name=props.get(
                        "canonical_name",
                        "",
                    ),
                    properties=props,
                )
            )

        edges: list[GraphEdge] = []

        for i, rel_data in enumerate(rels):
            props = (
                dict(rel_data)
                if hasattr(rel_data, "items")
                else rel_data
            )

            from_id = (
                nodes[i].node_id
                if i < len(nodes)
                else ""
            )

            to_id = (
                nodes[i + 1].node_id
                if i + 1 < len(nodes)
                else ""
            )

            rel_type = props.get(
                "type",
                "",
            )

            edges.append(
                self._edge_from_record(
                    props,
                    rel_type,
                    from_id,
                    to_id,
                )
            )

        path_length = record.get(
            "path_length",
            len(edges),
        )

        relevance = max(
            0.0,
            1.0 - (path_length * 0.15),
        )

        return GraphPath(
            nodes=nodes,
            edges=edges,
            relevance_score=relevance,
        )