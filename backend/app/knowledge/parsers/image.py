"""Image OCR parser with PaddleOCR primary and Tesseract fallback.

Strategy
--------
1. Attempt OCR using PaddleOCR (faster, better multilingual support for Indic scripts).
2. If PaddleOCR import fails or raises at runtime, fall back to pytesseract + Pillow.
3. If both fail, return an empty ParsedDocument with an error in extra_metadata.

PaddleOCR is optional at import time. This allows the application to run
without PaddleOCR installed (e.g. lightweight test environments), degrading
gracefully to Tesseract or returning empty text.

Supported MIME types: image/jpeg, image/png, image/tiff, image/webp, image/bmp.

Note: For scanned PDFs, the pipeline should render each page to a PNG image
      and feed it through this parser. That multi-page flow is handled by the
      IngestionPipeline — this parser itself only handles single-image inputs.
"""

from __future__ import annotations

import io
import time
from typing import Any

from loguru import logger

from app.knowledge.interfaces.parser import BaseParser, ParsedDocument, ParsedPage

# ── Optional dependency probes ────────────────────────────────────────────────

try:
    from paddleocr import PaddleOCR as _PaddleOCR

    _PADDLE_AVAILABLE = True
except ImportError:
    _PADDLE_AVAILABLE = False
    logger.warning("PaddleOCR not installed — will use Tesseract fallback for image OCR")

try:
    import pytesseract
    from PIL import Image as _PilImage

    _TESSERACT_AVAILABLE = True
except ImportError:
    _TESSERACT_AVAILABLE = False
    logger.warning("pytesseract / Pillow not installed — image OCR will return empty text")


class ImageParser:
    """OCR-based parser for image documents.

    PaddleOCR is used when available. Falls back to Tesseract + Pillow.
    Implements the BaseParser protocol.
    """

    _SUPPORTED_MIMES = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/tiff",
        "image/webp",
        "image/bmp",
    }

    def __init__(self, lang: str = "en") -> None:
        """
        Parameters
        ----------
        lang:
            Language hint for Tesseract (e.g. 'eng', 'hin', 'tam').
            PaddleOCR uses its own built-in language detection.
        """
        self._lang = lang
        self._paddle: Any | None = None

        if _PADDLE_AVAILABLE:
            try:
                # use_angle_cls=True improves rotated text detection
                self._paddle = _PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
                logger.info("ImageParser: PaddleOCR initialised (primary OCR engine)")
            except Exception as exc:
                logger.warning("ImageParser: PaddleOCR init failed ({}), using Tesseract", exc)
                self._paddle = None

    def supports(self, mime_type: str) -> bool:
        return mime_type.lower() in self._SUPPORTED_MIMES

    async def parse(self, file_bytes: bytes, filename: str) -> ParsedDocument:
        """Run OCR on an image and return extracted text.

        Tries PaddleOCR first; falls back to Tesseract if PaddleOCR
        is unavailable or raises an exception.
        """
        t0 = time.perf_counter()
        engine_used = "none"
        text = ""

        if self._paddle is not None:
            try:
                text, engine_used = self._paddle_ocr(file_bytes), "paddleocr"
            except Exception as exc:
                logger.warning(
                    "ImageParser: PaddleOCR failed on '{}': {} — falling back to Tesseract",
                    filename,
                    exc,
                )

        if not text and _TESSERACT_AVAILABLE:
            try:
                text, engine_used = self._tesseract_ocr(file_bytes), "tesseract"
            except Exception as exc:
                logger.error("ImageParser: Tesseract failed on '{}': {}", filename, exc)

        elapsed = time.perf_counter() - t0
        logger.info(
            "ImageParser: '{}' → {} chars in {:.3f}s (engine={})",
            filename,
            len(text),
            elapsed,
            engine_used,
        )

        if not text:
            logger.warning("ImageParser: no text extracted from '{}'", filename)

        return ParsedDocument(
            pages=[ParsedPage(page_number=1, text=text)],
            total_pages=1,
            mime_type=self._guess_mime(filename),
            extra_metadata={
                "parser": "image-ocr",
                "ocr_engine": engine_used,
                "ocr_duration_ms": f"{elapsed * 1000:.1f}",
                "filename": filename,
            },
        )

    # ── OCR engine implementations ────────────────────────────────────────

    def _paddle_ocr(self, file_bytes: bytes) -> str:
        """Run PaddleOCR on raw image bytes and concatenate results."""
        import numpy as np

        with _PilImage.open(io.BytesIO(file_bytes)) as img:
            img_array = np.array(img.convert("RGB"))

        results = self._paddle.ocr(img_array, cls=True)
        lines: list[str] = []

        if results and results[0]:
            for line in results[0]:
                # PaddleOCR result format: [[bbox], [text, confidence]]
                if line and len(line) >= 2:
                    text_conf = line[1]
                    if text_conf and len(text_conf) >= 1:
                        lines.append(str(text_conf[0]))

        return "\n".join(lines)

    def _tesseract_ocr(self, file_bytes: bytes) -> str:
        """Run pytesseract on raw image bytes."""
        with _PilImage.open(io.BytesIO(file_bytes)) as img:
            return pytesseract.image_to_string(img, lang=self._lang)

    @staticmethod
    def _guess_mime(filename: str) -> str:
        ext_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        from pathlib import Path

        suffix = Path(filename).suffix.lower()
        return ext_map.get(suffix, "image/jpeg")
