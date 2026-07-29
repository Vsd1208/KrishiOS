"""Configurable ranking engine for enterprise retrieval."""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.retrieval.interfaces.types import RankingSignals, RetrievalFilters, RetrievalHit


@dataclass(frozen=True, slots=True)
class RankingWeights:
    """Weights used to combine retrieval ranking signals."""

    semantic: float = 0.45
    authority: float = 0.15
    freshness: float = 0.15
    crop: float = 0.08
    state: float = 0.05
    district: float = 0.05
    season: float = 0.04
    language: float = 0.03


class RankingEngine:
    """Compute final retrieval scores beyond cosine similarity."""

    def __init__(self, weights: RankingWeights | None = None) -> None:
        self._weights = weights or RankingWeights()

    def score(self, hit: RetrievalHit, filters: RetrievalFilters) -> tuple[float, RankingSignals]:
        """Return final ranking score and component signals."""
        metadata = hit.metadata
        signals = RankingSignals(
            semantic_similarity=hit.similarity,
            authority_score=self._authority_score(metadata.get("authority")),
            freshness_score=self._freshness_score(metadata.get("indexed_at")),
            crop_match=self._match_score(filters.crop, metadata.get("crop")),
            state_match=self._match_score(filters.state, metadata.get("state")),
            district_match=self._match_score(filters.district, metadata.get("district")),
            season_match=self._match_score(filters.season, metadata.get("season")),
            language_match=self._match_score(filters.language, metadata.get("language")),
        )
        score = (
            signals.semantic_similarity * self._weights.semantic
            + signals.authority_score * self._weights.authority
            + signals.freshness_score * self._weights.freshness
            + signals.crop_match * self._weights.crop
            + signals.state_match * self._weights.state
            + signals.district_match * self._weights.district
            + signals.season_match * self._weights.season
            + signals.language_match * self._weights.language
        )
        return min(1.0, max(0.0, score)), signals

    @staticmethod
    def _match_score(expected: str | None, actual: object) -> float:
        if expected is None:
            return 0.5
        return 1.0 if str(actual or "").casefold() == expected.casefold() else 0.0

    @staticmethod
    def _authority_score(authority: object) -> float:
        value = str(authority or "").casefold()
        if any(name in value for name in ("icar", "government", "ministry", "university")):
            return 1.0
        if value:
            return 0.7
        return 0.4

    @staticmethod
    def _freshness_score(indexed_at: object) -> float:
        if indexed_at is None:
            return 0.5
        try:
            indexed = datetime.fromisoformat(str(indexed_at))
        except ValueError:
            return 0.5
        if indexed.tzinfo is None:
            indexed = indexed.replace(tzinfo=UTC)
        age_days = max(0, (datetime.now(UTC) - indexed).days)
        return max(0.2, 1.0 - min(age_days, 365) / 365)

