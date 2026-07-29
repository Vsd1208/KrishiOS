"""Query metadata extraction for retrieval filtering."""

from app.retrieval.interfaces.types import RetrievalFilters


class QueryMetadataExtractor:
    """Extract lightweight metadata hints from a query and explicit filters."""

    def merge(self, query: str, filters: RetrievalFilters) -> RetrievalFilters:
        """Merge explicit filters with conservative query-derived hints."""
        query_lower = query.casefold()
        season = filters.season
        if season is None:
            for candidate in ("kharif", "rabi", "zaid"):
                if candidate in query_lower:
                    season = candidate
                    break
        return RetrievalFilters(
            crop=filters.crop,
            state=filters.state,
            district=filters.district,
            season=season,
            language=filters.language,
            authority=filters.authority,
            document_type=filters.document_type,
            effective_at=filters.effective_at,
        )

