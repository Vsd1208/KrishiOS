"""Tests for retrieval index validation gates."""

import math

from app.retrieval.interfaces.types import IndexValidationReport, RetrievalHit
from app.retrieval.validation.validator import IndexValidator


def test_validation_report_requires_integrity() -> None:
    report = IndexValidationReport(
        precision=1.0,
        recall=1.0,
        mrr=1.0,
        ndcg=1.0,
        latency_ms=100,
        coverage=1.0,
        chunk_integrity=True,
        embedding_integrity=False,
    )

    assert not report.passed
    assert report.to_dict()["passed"] is False



class _FakeStore:
    """Returns a fixed ranking per query; the probe chunk sits at the given rank (or nowhere)."""

    def __init__(self, ranking: dict[str, list[str]]) -> None:
        self._ranking = ranking

    async def count(self, collection_name: str) -> int:
        return 3

    async def search(self, collection_name, query_vector, top_k, filters, score_threshold):
        ids = self._ranking[str(int(query_vector[0]))]
        return [RetrievalHit(chunk_id=i, chunk_text="", similarity=0.5, collection="c")
                for i in ids]


async def _embed(text: str) -> list[float]:
    return [float(text.split(maxsplit=1)[0])]


async def test_validation_measures_self_retrieval_not_counts() -> None:
    store = _FakeStore({"1": ["a", "x"], "2": ["x", "b"], "3": ["x", "y"]})
    report = await IndexValidator(store).validate(
        "c", expected_chunks=3, latency_ms=600_000.0,
        probes=[("a", "1 first passage"), ("b", "2 second"), ("c", "3 third")], embed_query=_embed)
    assert report.method == "self_retrieval" and report.probes == 3
    assert report.precision == 1 / 3  # only "a" at rank 1
    assert report.recall == 2 / 3  # "c" not in the top 5
    assert math.isclose(report.mrr, (1 + 1 / 2) / 3)
    assert math.isclose(report.ndcg, (1 + 1 / math.log2(3)) / 3)
    assert report.build_ms == 600_000.0 and report.latency_ms < 1500  # build time is not gated
    assert report.to_dict()["method"] == "self_retrieval"
