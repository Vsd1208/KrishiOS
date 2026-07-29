"""Tests for retrieval query metadata extraction."""

from app.retrieval.interfaces.types import RetrievalFilters
from app.retrieval.retrieval.metadata import QueryMetadataExtractor


def test_metadata_extractor_detects_season_when_filter_absent() -> None:
    extractor = QueryMetadataExtractor()
    filters = extractor.merge("best fertilizer for kharif rice", RetrievalFilters(crop="rice"))

    assert filters.season == "kharif"
    assert filters.crop == "rice"

