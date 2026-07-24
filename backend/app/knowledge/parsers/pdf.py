"""PDF parser using PyMuPDF (fitz).

PyMuPDF is the primary PDF parser because it:
* Handles complex layouts (multi-column, tables, mixed text+image).
* Preserves page boundaries natively.
* Extracts text in reading order without external layout analysis.
* Is significantly faster than pdfplumber or pdfminer for bulk ingestion.

For image-only PDFs (scanned documents), page text will be empty.
The image parser should be used instead, or pages can be rendered
to images and passed through PaddleOCR (future enhancement).

Each page's text is extracted with ``get_text("text")`` which gives
plain UTF-8 text with newlines preserved. Form-feed characters (\f)
are used as inter-page delimiters in ParsedDocument.full_text.
"""

from __future__ import annotations

import io

from loguru import logger

from app.knowledge.interfaces.parser import BaseParser, ParsedDocument, ParsedPage

try:
    import fitz  # PyMuPDF
except ImportError as exc:
    msg = "PyMuPDF is required for PDF parsing. Install it with: pip install pymupdf"
    raise ImportError(msg) from exc


class PdfParser:
    """Page-aware PDF text extractor using PyMuPDF.

    Implements the BaseParser protocol.
    """

    _SUPPORTED_MIMES = {"application/pdf"}

    def supports(self, mime_type: str) -> bool:
        return mime_type.lower() in self._SUPPORTED_MIMES

    async def parse(self, file_bytes: bytes, filename: str) -> ParsedDocument:
        """Extract text from every page of a PDF document.

        Parameters
        ----------
        file_bytes:
            Raw PDF binary content.
        filename:
            Original filename (used for logging only).

        Returns
        -------
        ParsedDocument
            One ParsedPage per PDF page.
            Pages with no extractable text have empty strings (scanned PDFs).
        """
        import time

        t0 = time.perf_counter()

        try:
            doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
        except Exception as exc:
            logger.error("PdfParser: failed to open '{}': {}", filename, exc)
            raise

        pages: list[ParsedPage] = []
        empty_pages: list[int] = []

        for page_index in range(len(doc)):
            page = doc[page_index]
            text = page.get_text("text").strip()
            page_number = page_index + 1

            pages.append(ParsedPage(page_number=page_number, text=text))

            if not text:
                empty_pages.append(page_number)

        doc.close()

        elapsed = time.perf_counter() - t0
        logger.info(
            "PdfParser: '{}' → {} pages in {:.3f}s"
            " (empty_pages={})",
            filename,
            len(pages),
            elapsed,
            empty_pages or "none",
        )

        if empty_pages:
            logger.warning(
                "PdfParser: {} page(s) have no text in '{}'. "
                "Document may be scanned — consider using the image parser.",
                len(empty_pages),
                filename,
            )

        return ParsedDocument(
            pages=pages,
            total_pages=len(pages),
            mime_type="application/pdf",
            extra_metadata={
                "parser": "pymupdf",
                "empty_pages": str(len(empty_pages)),
                "filename": filename,
            },
        )
