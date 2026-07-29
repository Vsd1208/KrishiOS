"""Citation construction for retrieved chunks."""

from app.retrieval.interfaces.types import Citation, RetrievalHit


class CitationBuilder:
    """Build citation metadata from retrieval payloads."""

    def build(self, hit: RetrievalHit) -> Citation:
        """Create a citation for a retrieval hit."""
        metadata = hit.metadata
        document_id = metadata.get("document_id")
        return Citation(
            document_id=int(document_id) if document_id is not None else None,
            title=self._optional_str(metadata.get("title")),
            source=self._optional_str(metadata.get("source")),
            source_url=self._optional_str(metadata.get("source_url")),
            page_number=self._optional_int(metadata.get("page_number")),
            chunk_id=hit.chunk_id,
        )

    @staticmethod
    def _optional_str(value: object) -> str | None:
        return str(value) if value is not None else None

    @staticmethod
    def _optional_int(value: object) -> int | None:
        if value is None:
            return None
        return int(value)
