"""Context construction for retrieval results."""

from app.retrieval.interfaces.types import RetrievalHit


class ContextBuilder:
    """Build answer context strings without generating answers."""

    def build(self, hit: RetrievalHit) -> str:
        """Return a compact context block for a retrieved chunk."""
        page = hit.metadata.get("page_number")
        title = hit.metadata.get("title")
        source = hit.metadata.get("source")
        prefix = " | ".join(str(value) for value in (title, source, f"page {page}") if value)
        if prefix:
            return f"{prefix}\n{hit.chunk_text}"
        return hit.chunk_text

