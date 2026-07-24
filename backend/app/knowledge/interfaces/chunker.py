"""Abstract chunker protocol.

Every chunking strategy (recursive, semantic) implements this protocol.
A chunker consumes cleaned text and produces discrete text segments with
provenance metadata for downstream embedding and vector storage.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class TextChunk:
    """A discrete segment of text ready for embedding.

    Attributes
    ----------
    chunk_index:
        0-based position of this chunk within its parent document.
    text:
        The actual chunk content. Length is bounded by the chunker's
        configured chunk_size (default 800 tokens / characters).
    page_number:
        Page this chunk originates from. Used for source attribution.
    token_count:
        Approximate token count using whitespace splitting.
        Exact tokenization is deferred to the embedding model.
    metadata:
        Arbitrary key/value pairs (crop, district, season, etc.) that
        will be stored as Qdrant payload alongside the vector.
    """

    chunk_index: int
    text: str
    page_number: int
    token_count: int
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ChunkerConfig:
    """Runtime parameters for any chunker implementation.

    Attributes
    ----------
    chunk_size:
        Maximum number of characters per chunk. Default: 800.
    chunk_overlap:
        Number of overlapping characters between consecutive chunks.
        Overlap preserves context across boundaries. Default: 120.
    """

    chunk_size: int = 800
    chunk_overlap: int = 120


@runtime_checkable
class BaseChunker(Protocol):
    """Contract that every text chunking strategy must satisfy."""

    def chunk(
        self,
        text: str,
        page_number: int,
        config: ChunkerConfig,
        extra_metadata: dict[str, str] | None = None,
    ) -> list[TextChunk]:
        """Split text into overlapping chunks with metadata.

        Parameters
        ----------
        text:
            Cleaned text to segment (output of the cleaning pipeline).
        page_number:
            Source page for provenance tracking.
        config:
            Chunk size and overlap settings.
        extra_metadata:
            Additional key/value pairs to attach to every chunk
            (e.g. crop name, district, season from document metadata).

        Returns
        -------
        list[TextChunk]
            Ordered list of text chunks with provenance.
        """
        ...
