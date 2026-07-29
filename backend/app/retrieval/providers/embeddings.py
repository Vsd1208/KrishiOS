"""SentenceTransformers embedding provider for retrieval workloads."""

import asyncio

from sentence_transformers import SentenceTransformer

from app.retrieval.interfaces.providers import EmbeddingProvider


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Dense embedding provider backed by Sentence Transformers."""

    def __init__(self, model_name: str, model_version: str) -> None:
        self._model_name = model_name
        self._model_version = model_version
        self._model = SentenceTransformer(model_name)

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
        vectors = self._model.encode(
            texts,
            batch_size=64,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]

