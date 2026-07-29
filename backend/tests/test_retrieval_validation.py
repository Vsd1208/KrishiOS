"""Tests for retrieval index validation gates."""

from app.retrieval.interfaces.types import IndexValidationReport


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

