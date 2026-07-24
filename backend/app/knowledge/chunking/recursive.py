"""Recursive character text splitter.

Uses LangChain's RecursiveCharacterTextSplitter with a separator hierarchy
that respects paragraph and sentence structure before falling back to
character-level splits.

Separator hierarchy (tried in order)
--------------------------------------
"\n\n"  — Paragraph boundary (strongest signal)
"\n"    — Line boundary
"। "    — Devanagari sentence terminator (Hindi, Marathi)
". "    — English sentence terminator
" "     — Word boundary
""      — Character-level (last resort, almost never reached)

Chunk size default: 800 characters
Overlap default   : 120 characters

Design note
-----------
LangChain is used here specifically for its mature recursive splitter.
No LangChain LLM, chain, or agent components are imported or used.
This is purely a text utility dependency.
"""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.knowledge.interfaces.chunker import BaseChunker, ChunkerConfig, TextChunk

# Separator hierarchy for agricultural documents (multilingual-aware)
_SEPARATORS = ["\n\n", "\n", "। ", ". ", " ", ""]


class RecursiveChunker:
    """Recursive character-based text chunker.

    Implements the BaseChunker protocol.
    Suitable for structured text (PDF, DOCX) where paragraph boundaries
    are meaningful and should be preserved.
    """

    def chunk(
        self,
        text: str,
        page_number: int,
        config: ChunkerConfig,
        extra_metadata: dict[str, str] | None = None,
    ) -> list[TextChunk]:
        """Split text into overlapping chunks using recursive character splitting.

        Parameters
        ----------
        text:
            Cleaned text for a single page (or the full document for single-page formats).
        page_number:
            1-based page number for provenance.
        config:
            Chunk size and overlap parameters.
        extra_metadata:
            Agricultural context to attach to each chunk.

        Returns
        -------
        list[TextChunk]
            Ordered list of overlapping text chunks.
        """
        if not text.strip():
            return []

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=_SEPARATORS,
            length_function=len,
            is_separator_regex=False,
        )

        raw_chunks: list[str] = splitter.split_text(text)
        metadata = extra_metadata or {}

        return [
            TextChunk(
                chunk_index=idx,
                text=chunk,
                page_number=page_number,
                token_count=len(chunk.split()),
                metadata=metadata,
            )
            for idx, chunk in enumerate(raw_chunks)
            if chunk.strip()
        ]
