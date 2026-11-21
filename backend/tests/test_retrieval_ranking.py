"""Tests for enterprise retrieval ranking behavior."""

from app.retrieval.interfaces.types import RetrievalFilters, RetrievalHit
from app.retrieval.ranking.engine import RankingEngine


def test_ranking_engine_combines_metadata_signals() -> None:
    engine = RankingEngine()
    hit = RetrievalHit(
        chunk_id="chunk-1",
        chunk_text="Rice blast disease management",
        similarity=0.8,
        collection="krishios-index-v001",
        metadata={
            "authority": "ICAR",
            "crop": "rice",
            "state": "Maharashtra",
            "district": "Pune",
            "season": "kharif",
            "language": "en",
        },
    )
    score, signals = engine.score(
        hit,
        RetrievalFilters(
            crop="rice",
            state="Maharashtra",
            district="Pune",
            season="kharif",
            language="en",
        ),
    )

    assert score > hit.similarity * 0.45
    assert signals.authority_score == 1.0
    assert signals.crop_match == 1.0



def test_crop_match_handles_synonyms_and_multi_crop_documents() -> None:
    engine = RankingEngine()
    hit = RetrievalHit(chunk_id="c", chunk_text="Top dressing of nitrogen", similarity=0.8,
                       collection="v", metadata={"crop": "paddy,cotton,maize"})
    for crop in ("rice", "Paddy", "maize", "corn"):
        assert engine.score(hit, RetrievalFilters(crop=crop))[1].crop_match == 1.0
    assert engine.score(hit, RetrievalFilters(crop="wheat"))[1].crop_match == 0.0


async def test_query_words_boost_but_never_filter() -> None:
    """A crop named in the question must not exclude passages (it returned nothing before)."""
    from app.retrieval.retrieval.metadata import QueryMetadataExtractor  # noqa: PLC0415
    from app.retrieval.retrieval.pipeline import EnterpriseRetrievalPipeline  # noqa: PLC0415

    seen: list[RetrievalFilters] = []

    class Store:
        async def search_alias(self, alias, vector, top_k, filters, threshold):
            seen.append(filters)
            return [RetrievalHit(chunk_id="c", chunk_text="Apply nitrogen in splits",
                                 similarity=0.8, collection="v", metadata={"crop": "paddy"})]

        async def get_alias_state(self, alias):
            class S:
                collection_name = None
            return S()

    class Embed:
        async def embed_query(self, q):
            return [0.0]

    class Rerank:
        async def rerank(self, q, hits):
            return hits

    class Builder:
        def build(self, hit):
            return None

    pipe = EnterpriseRetrievalPipeline.__new__(EnterpriseRetrievalPipeline)
    pipe._vector_store, pipe._embedding_provider, pipe._reranker = Store(), Embed(), Rerank()
    pipe._ranking_engine, pipe._metadata_extractor = RankingEngine(), QueryMetadataExtractor()
    pipe._context_builder = pipe._citation_builder = Builder()
    pipe._live_alias, pipe._delta_alias, pipe._multi_index_retriever = "live", "delta", None
    out = await pipe.search("When to top dress rice in kharif?", RetrievalFilters(), 3, 0.0,
                            include_delta=False)
    assert seen[0].crop is None and seen[0].season is None  # no hard filter from the question
    assert len(out.results) == 1
