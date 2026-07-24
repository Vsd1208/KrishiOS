"""Plain text parser.

Handles UTF-8, UTF-16, and Latin-1 text files. Encoding detection is
attempted in order: UTF-8 → UTF-16 → Latin-1. Latin-1 is a safe fallback
because it can decode any byte sequence (it maps bytes 0x00–0xFF directly).

The entire file is treated as a single page (page_number=1). If the text
contains multiple form-feed characters (\f), they are used to split into
logical pages for better provenance tracking.
"""

from __future__ import annotations

import time

from loguru import logger

from app.knowledge.interfaces.parser import BaseParser, ParsedDocument, ParsedPage


class TxtParser:
    """Plain text parser with multi-encoding fallback.

    Implements the BaseParser protocol.
    """

    _SUPPORTED_MIMES = {"text/plain", "text/csv"}

    # Encoding probe order: strictest first, safest last.
    _ENCODING_PROBE = ["utf-8", "utf-16", "latin-1"]

    def supports(self, mime_type: str) -> bool:
        return mime_type.lower() in self._SUPPORTED_MIMES

    async def parse(self, file_bytes: bytes, filename: str) -> ParsedDocument:
        """Decode text bytes and split on form-feed page markers.

        Parameters
        ----------
        file_bytes:
            Raw text file content.
        filename:
            Original filename (used for logging only).

        Returns
        -------
        ParsedDocument
            Multiple ParsedPage entries if \f characters are present,
            otherwise a single page containing the entire text.
        """
        t0 = time.perf_counter()

        text, encoding_used = self._decode(file_bytes, filename)
        pages = self._paginate(text)
        elapsed = time.perf_counter() - t0

        logger.info(
            "TxtParser: '{}' → {} page(s), {} chars in {:.3f}s (encoding={})",
            filename,
            len(pages),
            len(text),
            elapsed,
            encoding_used,
        )

        return ParsedDocument(
            pages=pages,
            total_pages=len(pages),
            mime_type="text/plain",
            extra_metadata={
                "parser": "txt-native",
                "encoding": encoding_used,
                "filename": filename,
            },
        )

    # ── Internal helpers ──────────────────────────────────────────────────

    def _decode(self, file_bytes: bytes, filename: str) -> tuple[str, str]:
        """Attempt to decode bytes using the encoding probe list."""
        for encoding in self._ENCODING_PROBE:
            try:
                return file_bytes.decode(encoding), encoding
            except (UnicodeDecodeError, ValueError):
                continue

        # Should never reach here since latin-1 always succeeds.
        logger.error("TxtParser: all encoding probes failed for '{}'", filename)
        raise ValueError(f"Cannot decode '{filename}' with any supported encoding")

    @staticmethod
    def _paginate(text: str) -> list[ParsedPage]:
        """Split text on form-feed characters into logical pages.

        If no form-feed characters are present, the entire text becomes
        a single page (page_number=1).
        """
        segments = text.split("\f")
        pages: list[ParsedPage] = []

        for i, segment in enumerate(segments, start=1):
            stripped = segment.strip()
            if stripped:
                pages.append(ParsedPage(page_number=i, text=stripped))

        return pages if pages else [ParsedPage(page_number=1, text=text)]
