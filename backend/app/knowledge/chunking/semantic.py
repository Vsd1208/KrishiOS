"""Semantic chunker — sentence-boundary-aware text segmentation.

Unlike the recursive splitter which splits on raw character counts,
the semantic chunker splits on sentence boundaries and then greedily
groups sentences into chunks that fit within the configured size limit.

This produces more coherent chunks for documents with long, complex
sentences (e.g. legal advisories, soil science reports) where a hard
character limit would split a sentence mid-thought.

Strategy
--------
1. Split text into sentences using a simple rule-based splitter
   (handles English '.' and Devanagari '।' terminators).
2. Greedily accumulate sentences until the chunk would exceed chunk_size.
3. When a boundary is reached, finalise the current chunk and start a new
   one with ``chunk_overlap`` characters of tail from the previous chunk.

No embedding model is used for similarity scoring in this version.
The "semantic" label refers to sentence-boundary awareness, not
vector-based semantic coherence (which would require an LLM/encoder).
"""

from __future__ import annotations

import re

from app.knowledge.interfaces.chunker import BaseChunker, ChunkerConfig, TextChunk

# Matches sentence-terminal punctuation followed by whitespace or end-of-string.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?।])\s+")


class SemanticChunker:
    """Sentence-boundary-aware text chunker.

    Implements the BaseChunker protocol.
    Best suited for narrative text (advisories, guidelines) where
    sentence coherence matters more than strict size boundaries.
    """

    def chunk(
        self,
        text: str,
        page_number: int,
        config: ChunkerConfig,
        extra_metadata: dict[str, str] | None = None,
    ) -> list[TextChunk]:
        """Split text on sentence boundaries with size-bounded grouping.

        Parameters
        ----------
        text:
            Cleaned text for one page.
        page_number:
            1-based page number for provenance.
        config:
            Chunk size and overlap parameters.
        extra_metadata:
            Agricultural context to attach to each chunk.

        Returns
        -------
        list[TextChunk]
            Sentence-coherent chunks within the configured size limit.
        """
        if not text.strip():
            return []

        sentences = _SENTENCE_SPLIT_RE.split(text.strip())
        metadata = extra_metadata or {}
        chunks: list[TextChunk] = []

        current_parts: list[str] = []
        current_len = 0
        chunk_index = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_len = len(sentence)

            # If adding this sentence would exceed chunk_size and we
            # already have content, flush the current chunk.
            if current_parts and (current_len + sentence_len + 1) > config.chunk_size:
                chunk_text = " ".join(current_parts)
                chunks.append(
                    TextChunk(
                        chunk_index=chunk_index,
                        text=chunk_text,
                        page_number=page_number,
                        token_count=len(chunk_text.split()),
                        metadata=metadata,
                    )
                )
                chunk_index += 1

                # Build overlap: take tail of current chunk up to overlap chars.
                overlap_text = chunk_text[-config.chunk_overlap :]
                current_parts = [overlap_text] if overlap_text.strip() else []
                current_len = len(overlap_text)

            current_parts.append(sentence)
            current_len += sentence_len + 1  # +1 for joining space

        # Flush remaining content
        if current_parts:
            chunk_text = " ".join(current_parts)
            if chunk_text.strip():
                chunks.append(
                    TextChunk(
                        chunk_index=chunk_index,
                        text=chunk_text,
                        page_number=page_number,
                        token_count=len(chunk_text.split()),
                        metadata=metadata,
                    )
                )

        return chunks
