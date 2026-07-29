"""Cross-encoder reranking provider."""

import asyncio

from sentence_transformers import CrossEncoder

from app.retrieval.interfaces.providers import RerankerProvider
from app.retrieval.interfaces.types import RetrievalHit


class CrossEncoderReranker(RerankerProvider):
    """Rerank retrieval hits using a SentenceTransformers cross encoder."""

    def __init__(self, model_name: str) -> None:
        self._model = CrossEncoder(model_name)

    async def rerank(self, query: str, hits: list[RetrievalHit]) -> list[RetrievalHit]:
        """Return hits sorted by cross-encoder relevance score."""
        if not hits:
            return []
        scores = await asyncio.to_thread(
            self._model.predict,
            [(query, hit.chunk_text) for hit in hits],
        )
        paired = sorted(zip(hits, scores, strict=True), key=lambda item: float(item[1]), reverse=True)
        reranked: list[RetrievalHit] = []
        for hit, score in paired:
            metadata = dict(hit.metadata)
            metadata["rerank_score"] = float(score)
            reranked.append(
                RetrievalHit(
                    chunk_id=hit.chunk_id,
                    chunk_text=hit.chunk_text,
                    similarity=hit.similarity,
                    collection=hit.collection,
                    metadata=metadata,
                )
            )
        return reranked

