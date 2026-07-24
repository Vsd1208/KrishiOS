"""Text cleaning pipeline.

Normalises raw extracted text before it enters the chunking stage.
Each cleaner is a pure function (str → str) applied sequentially.
The pipeline is stateless and safe to call concurrently.

Cleaning steps (in order)
--------------------------
1. Unicode normalisation (NFC) — fixes composed vs decomposed forms.
2. Remove null bytes and control characters (except \n, \t, \f).
3. Fix common OCR artefacts (ligatures, garbled punctuation).
4. Remove repeated headers/footers (heuristic: lines repeated > N times).
5. Collapse multiple blank lines into a maximum of two.
6. Strip leading/trailing whitespace from each line.
7. Collapse intra-line whitespace runs to a single space.

What is NOT removed
--------------------
* Page numbers (kept for provenance — chunker uses them).
* Newlines (structural signal for paragraph detection).
* Non-ASCII characters (critical for Indic language support).
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter


# ── OCR ligature / artefact map ───────────────────────────────────────────────

_OCR_REPLACEMENTS: dict[str, str] = {
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬀ": "ff",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    "ﬅ": "ft",
    "ﬆ": "st",
    "\u2019": "'",   # Right single quotation → apostrophe
    "\u2018": "'",   # Left single quotation
    "\u201c": '"',   # Left double quotation
    "\u201d": '"',   # Right double quotation
    "\u2013": "-",   # En dash
    "\u2014": "--",  # Em dash
    "\u00ad": "",    # Soft hyphen (invisible)
    "\ufffd": "",    # Unicode replacement character (encoding error)
}

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_BLANK_LINE_RE = re.compile(r"\n{3,}")


# ── Public API ────────────────────────────────────────────────────────────────


class TextCleaner:
    """Stateless text cleaning pipeline.

    Parameters
    ----------
    max_blank_lines:
        Maximum consecutive blank lines to allow. Extra blanks are collapsed.
    header_footer_threshold:
        If a line appears more than this many times in the document,
        it is treated as a repeated header/footer and removed.
    """

    def __init__(
        self,
        max_blank_lines: int = 2,
        header_footer_threshold: int = 3,
    ) -> None:
        self._max_blank_lines = max_blank_lines
        self._header_footer_threshold = header_footer_threshold

    def clean(self, text: str) -> str:
        """Apply the full cleaning pipeline to raw extracted text.

        Parameters
        ----------
        text:
            Raw text from the document parser.

        Returns
        -------
        str
            Cleaned, normalised text ready for chunking.
        """
        text = self._normalize_unicode(text)
        text = self._remove_control_chars(text)
        text = self._fix_ocr_artifacts(text)
        text = self._remove_repeated_lines(text)
        text = self._clean_lines(text)
        text = self._collapse_blank_lines(text)
        return text.strip()

    # ── Pipeline steps ────────────────────────────────────────────────────

    @staticmethod
    def _normalize_unicode(text: str) -> str:
        """Apply NFC normalisation to canonicalise composed characters."""
        return unicodedata.normalize("NFC", text)

    @staticmethod
    def _remove_control_chars(text: str) -> str:
        """Strip control characters while preserving \n, \t, and \f."""
        return _CONTROL_CHAR_RE.sub("", text)

    @staticmethod
    def _fix_ocr_artifacts(text: str) -> str:
        """Replace known OCR ligatures and typographic artefacts."""
        for bad, good in _OCR_REPLACEMENTS.items():
            text = text.replace(bad, good)
        return text

    def _remove_repeated_lines(self, text: str) -> str:
        """Remove lines that recur more than the threshold times.

        This targets running headers and footers that appear on every page.
        Lines shorter than 5 characters are ignored (page numbers, etc.).
        """
        lines = text.split("\n")
        line_counts: Counter[str] = Counter(
            line.strip() for line in lines if len(line.strip()) >= 5
        )
        repeated = {
            line
            for line, count in line_counts.items()
            if count > self._header_footer_threshold
        }
        if not repeated:
            return text
        return "\n".join(
            line for line in lines if line.strip() not in repeated
        )

    @staticmethod
    def _clean_lines(text: str) -> str:
        """Strip each line and collapse internal whitespace runs."""
        cleaned: list[str] = []
        for line in text.split("\n"):
            line = _MULTI_SPACE_RE.sub(" ", line).strip()
            cleaned.append(line)
        return "\n".join(cleaned)

    def _collapse_blank_lines(self, text: str) -> str:
        """Collapse runs of more than max_blank_lines blank lines."""
        replacement = "\n" * (self._max_blank_lines + 1)
        return _MULTI_BLANK_LINE_RE.sub(replacement, text)
