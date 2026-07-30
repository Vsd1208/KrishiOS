"""Query metadata extraction for retrieval filtering."""

from app.retrieval.interfaces.types import RetrievalFilters


class QueryMetadataExtractor:
    """Extract lightweight metadata hints from a query and explicit filters."""

    def merge(self, query: str, filters: RetrievalFilters) -> RetrievalFilters:
        """Merge explicit filters with conservative query-derived hints."""
        query_lower = query.casefold()
        crop = filters.crop
        state = filters.state
        district = filters.district
        season = filters.season
        language = filters.language

        if crop is None:
            for candidate in ("rice", "wheat", "maize", "cotton", "sugarcane", "pulses"):
                if candidate in query_lower:
                    crop = candidate
                    break
        if state is None:
            for candidate in ("maharashtra", "punjab", "uttar pradesh", "karnataka", "tamil nadu"):
                if candidate in query_lower:
                    state = candidate
                    break
        if district is None:
            for candidate in ("pune", "amritsar", "lucknow", "bangalore", "chennai"):
                if candidate in query_lower:
                    district = candidate
                    break
        if season is None:
            for candidate in ("kharif", "rabi", "zaid"):
                if candidate in query_lower:
                    season = candidate
                    break
        if language is None and any(token in query_lower for token in ("hindi", "marathi", "punjabi", "tamil", "telugu")):
            for candidate in ("hi", "mr", "pa", "ta", "te"):
                if candidate in query_lower:
                    language = candidate
                    break

        return RetrievalFilters(
            crop=crop,
            state=state,
            district=district,
            season=season,
            language=language,
            authority=filters.authority,
            document_type=filters.document_type,
            effective_at=filters.effective_at,
        )

