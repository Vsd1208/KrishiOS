"""Knowledge Infrastructure package for KrishiOS.

This package contains the complete document ingestion and semantic search layer.
No LLM, no RAG answer generation, no agents — only the AI data foundation.

Sub-packages
------------
interfaces   — Abstract protocols for parser, chunker, and vector store.
parsers      — Format-specific document parsers (PDF, DOCX, TXT, Image).
ingestion    — Text cleaning pipeline.
chunking     — Recursive and semantic chunking strategies.
embeddings   — Sentence Transformers batch embedding pipeline.
vectorstore  — Qdrant vector database client and collection management.
metadata     — Agricultural metadata extractor (crop, district, season).
retrieval    — Top-K semantic search with metadata filtering.
storage      — File persistence layer with SHA-256 deduplication.
pipelines    — Full ingestion orchestrator (parse→clean→chunk→embed→store).
"""
