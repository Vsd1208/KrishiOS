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

