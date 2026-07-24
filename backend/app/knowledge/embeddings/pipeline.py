"""Sentence Transformers embedding pipeline.

Wraps sentence-transformers to produce dense vector embeddings from
text chunks. No LLM, no OpenAI API, no external network call at
inference time (model is cached locally after first download).

Default model: sentence-transformers/all-MiniLM-L6-v2
  - 384 dimensions
  - 80 MB model size
  - ~14,000 sentences/second on CPU
  - Strong performance on semantic similarity tasks

Design decisions
----------------
* Model is loaded ONCE and reused across all requests (singleton pattern).
* Batched encoding via `model.encode(batch)` for throughput.
* Retry logic with exponential back-off handles transient OOM errors
  on large batches (reduces batch size on each retry).
* `normalize_embeddings=True` is set so cosine similarity == dot product.
  This is required for Qdrant's COSINE distance metric.
* The embedding model name and version are stored alongside each chunk
  so future model upgrades can be tracked and chunks re-embedded selectively.
"""

from __future__ import annotations

import time
from functools import lru_cache

import numpy as np
from loguru import logger
from sentence_transformers import SentenceTransformer

from app.knowledge.interfaces.chunker import TextChunk
from app.knowledge.interfaces.vectorstore import VectorPoint

# Re-export for convenience
__all__ = ["EmbeddingPipeline"]

# ── Model version tag ──────────────────────────────────────────────────────────
# Bump this when the model weights or tokeniser changes so cached chunks
# can be invalidated and re-embedded.
_DEFAULT_MODEL = "all-MiniLM-L6-v2"
_MODEL_VERSION = "v1"

# ── Retry constants ───────────────────────────────────────────────────────────
_MAX_RETRIES = 3
_INITIAL_BATCH_SIZE = 64


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> SentenceTransformer:
    """Load (or return cached) a SentenceTransformer model.

    lru_cache ensures a maximum of 4 different models are kept in memory.
    In practice, KrishiOS uses exactly one model.
    """
    logger.info("EmbeddingPipeline: loading model '{}'", model_name)
    t0 = time.perf_counter()
    model = SentenceTransformer(model_name)
    logger.info(
        "EmbeddingPipeline: model '{}' loaded in {:.2f}s (dim={})",
        model_name,
        time.perf_counter() - t0,
        model.get_sentence_embedding_dimension(),
    )
    return model


class EmbeddingPipeline:
    """Batch embedding pipeline using Sentence Transformers.

    Parameters
    ----------
    model_name:
        Sentence Transformers model identifier.
    model_version:
        Version tag stored alongside each chunk for cache invalidation.
    """

    def __init__(
        self,
        model_name: str = _DEFAULT_MODEL,
        model_version: str = _MODEL_VERSION,
    ) -> None:
        self._model_name = model_name
        self._model_version = model_version
        # Trigger model load eagerly so the first request doesn't pay the cost.
        self._model = _load_model(model_name)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def embedding_dimension(self) -> int:
        """Return the output vector dimensionality of the loaded model."""
        return self._model.get_sentence_embedding_dimension()  # type: ignore[return-value]

    def embed_chunks(
        self,
        chunks: list[TextChunk],
        document_id: str,
        document_uuid: str,
        extra_payload: dict[str, str | int | float | bool] | None = None,
    ) -> list[VectorPoint]:
        """Embed a list of TextChunks and return ready-to-upsert VectorPoints.

        Parameters
        ----------
        chunks:
            Text chunks from the chunking pipeline.
        document_id:
            Integer document ID (as string) for Qdrant payload.
        document_uuid:
            UUID of the parent KnowledgeDocument.
        extra_payload:
            Additional Qdrant payload fields (language, crop, district, etc.).

        Returns
        -------
        list[VectorPoint]
            One VectorPoint per input chunk, ready for Qdrant upsert.
        """
        if not chunks:
            return []

        t0 = time.perf_counter()
        texts = [c.text for c in chunks]
        vectors = self._encode_with_retry(texts)

        points: list[VectorPoint] = []
        base_payload = extra_payload or {}

        from uuid import uuid4

        for chunk, vector in zip(chunks, vectors, strict=True):
            point_id = uuid4()  # Each chunk gets its own UUID → synced to DocumentChunk.chunk_id
            payload: dict[str, str | int | float | bool] = {
                "document_id": document_uuid,
                "chunk_id": str(point_id),
                "chunk_text": chunk.text,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "token_count": chunk.token_count,
                "embedding_model": self._model_name,
                **{k: str(v) for k, v in chunk.metadata.items()},
                **base_payload,
            }
            points.append(VectorPoint(point_id=point_id, vector=vector, payload=payload))

        elapsed = time.perf_counter() - t0
        logger.info(
            "EmbeddingPipeline: embedded {} chunks in {:.3f}s (model='{}')",
            len(chunks),
            elapsed,
            self._model_name,
        )
        return points

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query string for search.

        Parameters
        ----------
        query:
            Raw search query text.

        Returns
        -------
        list[float]
            Normalised embedding vector.
        """
        vector: np.ndarray = self._model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]
        return vector.tolist()

    # ── Internal helpers ──────────────────────────────────────────────────

    def _encode_with_retry(self, texts: list[str]) -> list[list[float]]:
        """Encode texts with batch-size reduction on failure.

        On OOM or encoding errors, the batch size is halved and encoding
        is retried up to _MAX_RETRIES times.
        """
        batch_size = _INITIAL_BATCH_SIZE
        last_error: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                embeddings: np.ndarray = self._model.encode(
                    texts,
                    batch_size=batch_size,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                return [e.tolist() for e in embeddings]
            except Exception as exc:
                last_error = exc
                batch_size = max(1, batch_size // 2)
                logger.warning(
                    "EmbeddingPipeline: attempt {}/{} failed (batch_size→{}): {}",
                    attempt,
                    _MAX_RETRIES,
                    batch_size,
                    exc,
                )

        raise RuntimeError(
            f"EmbeddingPipeline: all {_MAX_RETRIES} encoding attempts failed"
        ) from last_error
