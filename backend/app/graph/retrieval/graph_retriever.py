"""High-level graph retrieval interface over GraphStore.

Provides domain-specific queries (e.g. "query_by_symptoms") using
the underlying GraphStore primitives.
"""

from __future__ import annotations

import time

from app.graph.interfaces.store import GraphStore
from app.graph.interfaces.types import (
    GraphEntity, # type: ignore
    GraphNode,
    GraphPath,
    GraphRetrievalResult,
    GRAPH_STATUS_ACTIVE,
)
from app.graph.extraction.types import ResolvedEntity


class GraphRetriever:
    """Provides high-level knowledge retrieval over the graph store."""

    def __init__(self, store: GraphStore) -> None:
        self._store = store

    async def retrieve_for_entities(self, query: str, entities: list[ResolvedEntity]) -> GraphRetrievalResult:
        """Find relevant graph paths and nodes for a set of query entities.
        
        This is the main entry point for GraphRAG fusion.
        """
        start = time.perf_counter()
        
        all_paths: list[GraphPath] = []
        all_nodes: dict[str, GraphNode] = {}
        
        for entity in entities:
            # Find the starting node in the graph
            nodes = await self._store.find_nodes_by_name(
                label=entity.entity_type,
                name=entity.canonical_name,
                fuzzy=False,
            )
            
            for node in nodes:
                all_nodes[node.node_id] = node
                
                # Expand to neighbors (depth 1)
                neighbors = await self._store.get_neighbors(
                    node_id=node.node_id,
                    depth=1,
                    status=GRAPH_STATUS_ACTIVE,
                )
                for n in neighbors:
                    all_nodes[n.node_id] = n
                    
                # Find specific paths based on entity type
                # E.g. if it's a Crop, find diseases
                if entity.entity_type == "Crop":
                    paths = await self._store.find_paths(
                        from_node_id=node.node_id,
                        to_label="Disease",
                        max_hops=2,
                        status=GRAPH_STATUS_ACTIVE,
                    )
                    all_paths.extend(paths)
                
                # If it's a Symptom, find Diseases (backwards traversal)
                # (For MVP, find_paths defaults to OUTGOING. In a real system,
                # we might need undirected or INCOMING path queries.)
        
        # Deduplicate paths (naive deduplication by path_text)
        unique_paths: dict[str, GraphPath] = {}
        for path in all_paths:
            if path.path_text not in unique_paths:
                unique_paths[path.path_text] = path
                
        latency_ms = (time.perf_counter() - start) * 1000
        
        return GraphRetrievalResult(
            query=query,
            paths=list(unique_paths.values()),
            entities=list(all_nodes.values()),
            latency_ms=latency_ms,
        )
