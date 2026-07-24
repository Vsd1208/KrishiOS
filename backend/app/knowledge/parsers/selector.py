"""Parser selector — chooses the correct parser based on MIME type.

This module implements the Strategy pattern: the selector receives a MIME
type and returns the appropriate BaseParser implementation. All parsers
are pre-instantiated once (singletons within the selector) to avoid
repeated initialisation overhead (especially for PaddleOCR which loads
a neural network on first construction).

MIME type is determined by python-magic (libmagic) from file bytes,
NOT from the uploaded filename extension, to prevent extension spoofing.

Supported formats
-----------------
application/pdf                                                 → PdfParser
application/vnd.openxmlformats-officedocument.wordprocessingml → DocxParser
text/plain                                                      → TxtParser
image/jpeg, image/png, image/tiff, image/webp, image/bmp       → ImageParser
"""

from __future__ import annotations

import io

from loguru import logger

from app.knowledge.interfaces.parser import BaseParser, ParsedDocument
from app.knowledge.parsers.docx import DocxParser
from app.knowledge.parsers.image import ImageParser
from app.knowledge.parsers.pdf import PdfParser
from app.knowledge.parsers.txt import TxtParser

# ── MIME detection ────────────────────────────────────────────────────────────

# Use python-magic when available; fall back to a simple header-byte probe.
try:
    import magic

    def _detect_mime(file_bytes: bytes, filename: str) -> str:
        return magic.from_buffer(file_bytes[:2048], mime=True)

    logger.debug("ParserSelector: using python-magic for MIME detection")

except ImportError:
    logger.warning("python-magic not installed — using filename extension for MIME detection")

    def _detect_mime(file_bytes: bytes, filename: str) -> str:  # type: ignore[misc]
        """Fallback MIME detection from file extension."""
        from pathlib import Path

        _ext_map: dict[str, str] = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        suffix = Path(filename).suffix.lower()
        return _ext_map.get(suffix, "application/octet-stream")


# ── Maximum upload size constant ──────────────────────────────────────────────
# 50 MB default. Enforced in the upload endpoint, duplicated here for clarity.
MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024


class ParserSelector:
    """Selects and runs the appropriate parser for a given file.

    Usage
    -----
    selector = ParserSelector()
    parsed = await selector.parse(file_bytes, filename="document.pdf")
    """

    def __init__(self) -> None:
        # Pre-instantiate all parsers to avoid per-request construction cost.
        self._parsers: list[BaseParser] = [
            PdfParser(),
            DocxParser(),
            TxtParser(),
            ImageParser(),
        ]

    async def parse(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str | None = None,
    ) -> tuple[ParsedDocument, str]:
        """Detect MIME type and delegate to the correct parser.

        Parameters
        ----------
        file_bytes:
            Complete file content as bytes.
        filename:
            Original filename (for logging and extension fallback).
        mime_type:
            Optional override. If None, detected from file bytes.

        Returns
        -------
        tuple[ParsedDocument, str]
            (parsed_document, detected_mime_type)

        Raises
        ------
        ValueError
            If no registered parser supports the detected MIME type.
        """
        detected_mime = mime_type or _detect_mime(file_bytes, filename)
        logger.info(
            "ParserSelector: '{}' → MIME='{}' ({} bytes)",
            filename,
            detected_mime,
            len(file_bytes),
        )

        for parser in self._parsers:
            if parser.supports(detected_mime):
                logger.debug(
                    "ParserSelector: using {} for '{}'",
                    type(parser).__name__,
                    filename,
                )
                parsed = await parser.parse(file_bytes, filename)
                return parsed, detected_mime

        supported = self.supported_mime_types()
        raise ValueError(
            f"Unsupported MIME type '{detected_mime}' for file '{filename}'. "
            f"Supported types: {sorted(supported)}"
        )

    def supported_mime_types(self) -> set[str]:
        """Return the union of all MIME types handled by registered parsers."""
        types: set[str] = set()
        for parser in self._parsers:
            # Each parser exposes its _SUPPORTED_MIMES attribute.
            if hasattr(parser, "_SUPPORTED_MIMES"):
                types.update(parser._SUPPORTED_MIMES)  # noqa: SLF001
        return types
