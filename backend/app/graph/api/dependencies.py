"""Dependencies for the Graph module."""

from __future__ import annotations

from app.graph.interfaces.store import GraphStore

# Global singleton populated during application startup
_GRAPH_STORE: GraphStore | None = None


def set_graph_store(store: GraphStore | None) -> None:
    """Set the global graph store instance."""
    global _GRAPH_STORE
    _GRAPH_STORE = store


def get_graph_store() -> GraphStore:
    """Get the global graph store instance."""
    if _GRAPH_STORE is None:
        raise RuntimeError("Graph store is not initialized")
    return _GRAPH_STORE
