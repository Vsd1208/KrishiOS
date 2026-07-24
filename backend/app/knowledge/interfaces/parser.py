"""Abstract parser protocol.

Every document parser (PDF, DOCX, TXT, Image) implements this protocol.
A parser is responsible for extracting raw text from a binary document
while preserving page-level provenance required for chunk metadata.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ParsedPage:
    """A single page of text extracted from a document.

    Attributes
    ----------
    page_number:
        1-based page index. For formats without pagination (TXT, DOCX),
        the entire document is represented as a single page (page_number=1).
    text:
        Raw extracted text for this page. May contain OCR noise; the
        cleaning pipeline handles normalization downstream.
    """

    page_number: int
    text: str


@dataclass(slots=True)
class ParsedDocument:
    """Result produced by any BaseParser implementation.

    Attributes
    ----------
    pages:
        Ordered list of extracted pages.
    total_pages:
        Total page count (equals len(pages) for most parsers).
    mime_type:
        MIME type as detected by the parser.
    extra_metadata:
        Parser-specific key/value pairs (e.g. PDF author, OCR engine used).
    """

    pages: list[ParsedPage] = field(default_factory=list)
    total_pages: int = 0
    mime_type: str = ""
    extra_metadata: dict[str, str] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """Concatenate all pages separated by a form-feed character."""
        return "\f".join(p.text for p in self.pages)


@runtime_checkable
class BaseParser(Protocol):
    """Contract that every document parser must satisfy.

    Implementations must be stateless and safe to call concurrently.
    """

    async def parse(self, file_bytes: bytes, filename: str) -> ParsedDocument:
        """Extract text and page structure from raw file bytes.

        Parameters
        ----------
        file_bytes:
            The complete binary content of the uploaded file.
        filename:
            Original filename, used for format hints and metadata.

        Returns
        -------
        ParsedDocument
            Structured result with per-page text and metadata.
        """
        ...

    def supports(self, mime_type: str) -> bool:
        """Return True if this parser handles the given MIME type."""
        ...
