"""SentenceTransformers embedding provider for retrieval workloads."""

import asyncio
import hashlib
import math
from typing import Any

from app.retrieval.interfaces.providers import EmbeddingProvider

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - exercised in lightweight environments
    SentenceTransformer = None  # type: ignore[assignment]


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Dense embedding provider backed by Sentence Transformers or a deterministic fallback."""

    def __init__(self, model_name: str, model_version: str) -> None:
        self._model_name = model_name
        self._model_version = model_version
        self._model: Any | None = (
            SentenceTransformer(
                model_name,
                device="cpu",
                model_kwargs={"low_cpu_mem_usage": False},
            )
            if SentenceTransformer is not None
            else None
        )

    @property
    def model_name(self) -> str:
        """Return the configured model name."""
        return self._model_name

    @property
    def model_version(self) -> str:
        """Return the configured model version."""
        return self._model_version

    @property
    def vector_size(self) -> int:
        """Return the embedding dimensionality."""
        if self._model is None:
            return 32
        return int(self._model.get_sentence_embedding_dimension())

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts without blocking the event loop."""
        if not texts:
            return []
        return await asyncio.to_thread(self._encode, texts)

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single retrieval query."""
        vectors = await self.embed_texts([query])
        return vectors[0]

    def _encode(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            return [self._fallback_encode(text) for text in texts]

        vectors = self._model.encode(
            texts,
            batch_size=64,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]

    @staticmethod
    def _fallback_encode(text: str) -> list[float]:
        tokens = [
            token.casefold()
            for token in text.replace("\n", " ").split()
            if token
        ]

        if not tokens:
            return [0.0] * 32

        vector = [0.0] * 32

        for index, token in enumerate(tokens):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:2], "big") % 32
            magnitude = 1.0 / (1 + index)
            vector[bucket] += magnitude

        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]