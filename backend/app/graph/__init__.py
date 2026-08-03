"""Sprint 6 — Agricultural Knowledge Graph and GraphRAG layer.

This package provides:
  - GraphStore abstraction over Neo4j
  - Agricultural ontology (entities + relationships)
  - Entity extraction and resolution
  - Relationship extraction with controlled predicates
  - Knowledge validation before graph insertion
  - Graph ingestion stage (extends Sprint 2 pipeline)
  - Graph retrieval (Neo4j traversal)
  - Hybrid GraphRAG pipeline (vector + graph fusion)
  - Graph knowledge tool for Sprint 4 agents
  - REST API for graph entities, relationships, and officer review
"""
