"""Chunking pipeline orchestrator.

Selects the appropriate chunking strategy based on document type and
runs it over all parsed pages, re-indexing chunk_index globally across
the full document (not per-page).

Strategy selection
------------------
- document_type == "research" or page count >= 10  → RecursiveChunker
  (better for long structured documents with headings and references)
- All other documents                               → SemanticChunker
  (better for narrative advisories and guidelines)

The selection can be overridden by passing strategy="recursive" or
strategy="semantic" explicitly.

Global chunk index
------------------
Each ParsedPage is chunked independently. Chunk indices are then
renumbered globally across all pages so that chunk_index is monotonically
increasing within a single document. This makes the chunk position
unambiguous even when a document has many short pages.
"""

from __future__ import annotations

from app.knowledge.interfaces.chunker import ChunkerConfig, TextChunk
from app.knowledge.interfaces.parser import ParsedDocument
from app.knowledge.chunking.recursive import RecursiveChunker
from app.knowledge.chunking.semantic import SemanticChunker


class ChunkingPipeline:
    """Orchestrates strategy selection and per-page chunking.

    Parameters
    ----------
    config:
        Shared chunk size and overlap configuration.
    """

    def __init__(self, config: ChunkerConfig | None = None) -> None:
        self._config = config or ChunkerConfig()
        self._recursive = RecursiveChunker()
        self._semantic = SemanticChunker()

    def run(
        self,
        parsed: ParsedDocument,
        document_type: str = "general",
        extra_metadata: dict[str, str] | None = None,
        strategy: str | None = None,
    ) -> list[TextChunk]:
        """Chunk all pages in the parsed document.

        Parameters
        ----------
        parsed:
            Output of any BaseParser implementation.
        document_type:
            Used for automatic strategy selection when strategy is None.
        extra_metadata:
            Key/value pairs to attach to every chunk (crop, district, etc.).
        strategy:
            Force "recursive" or "semantic". If None, auto-selected.

        Returns
        -------
        list[TextChunk]
            All chunks across all pages, globally re-indexed.
        """
        chunker = self._select_strategy(strategy, document_type, parsed)
        all_chunks: list[TextChunk] = []

        for page in parsed.pages:
            page_chunks = chunker.chunk(
                text=page.text,
                page_number=page.page_number,
                config=self._config,
                extra_metadata=extra_metadata,
            )
            all_chunks.extend(page_chunks)

        # Re-number chunk_index globally across the full document.
        reindexed: list[TextChunk] = []
        for global_idx, chunk in enumerate(all_chunks):
            reindexed.append(
                TextChunk(
                    chunk_index=global_idx,
                    text=chunk.text,
                    page_number=chunk.page_number,
                    token_count=chunk.token_count,
                    metadata=chunk.metadata,
                )
            )

        return reindexed

    # ── Strategy selection ────────────────────────────────────────────────

    def _select_strategy(
        self,
        strategy: str | None,
        document_type: str,
        parsed: ParsedDocument,
    ) -> RecursiveChunker | SemanticChunker:
        """Return the chunker to use based on explicit or heuristic selection."""
        if strategy == "recursive":
            return self._recursive
        if strategy == "semantic":
            return self._semantic

        # Auto-select: research docs or long docs → recursive
        is_research = document_type.lower() in {"research", "report", "guideline"}
        is_long = parsed.total_pages >= 10

        return self._recursive if (is_research or is_long) else self._semantic
