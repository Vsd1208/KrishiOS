"""Cross-encoder reranking provider."""

import asyncio
from typing import Any

from app.retrieval.interfaces.providers import RerankerProvider
from app.retrieval.interfaces.types import RetrievalHit

try:
    from sentence_transformers import CrossEncoder
except ImportError:  # pragma: no cover - exercised in lightweight environments
    CrossEncoder = None  # type: ignore[assignment]


class CrossEncoderReranker(RerankerProvider):
    """Rerank retrieval hits using a SentenceTransformers cross encoder or simple fallback."""

    def __init__(self, model_name: str) -> None:
        self._model: Any | None = CrossEncoder(model_name) if CrossEncoder is not None else None

    async def rerank(self, query: str, hits: list[RetrievalHit]) -> list[RetrievalHit]:
        """Return hits sorted by cross-encoder relevance score."""
        if not hits:
            return []
        if self._model is None:
            reranked = sorted(hits, key=lambda hit: self._fallback_score(query, hit), reverse=True)
        else:
            scores = await asyncio.to_thread(
                self._model.predict,
                [(query, hit.chunk_text) for hit in hits],
            )
            paired = sorted(zip(hits, scores, strict=True), key=lambda item: float(item[1]), reverse=True)
            reranked = [
                RetrievalHit(
                    chunk_id=hit.chunk_id,
                    chunk_text=hit.chunk_text,
                    similarity=hit.similarity,
                    collection=hit.collection,
                    metadata={**hit.metadata, "rerank_score": float(score)},
                )
                for hit, score in paired
            ]
        return reranked

    @staticmethod
    def _fallback_score(query: str, hit: RetrievalHit) -> float:
        query_tokens = {token.casefold() for token in query.split() if token}
        hit_tokens = {token.casefold() for token in hit.chunk_text.split() if token}
        overlap = len(query_tokens & hit_tokens)
        return hit.similarity + (overlap * 0.05)

