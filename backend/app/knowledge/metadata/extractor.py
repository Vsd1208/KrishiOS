"""Agricultural metadata extractor.

Derives structured metadata (crop, district, season, language) from
the raw text of a parsed document. This is a heuristic, keyword-based
extractor — no LLM or ML model is involved.

The extracted metadata is merged with any metadata explicitly provided
at upload time. Upload-time metadata always takes precedence.

Design decision
---------------
Using a simple keyword scan rather than NER/LLM extraction keeps the
system deterministic and avoids adding an LLM dependency to this sprint.
The Sprint 2 Definition of Done explicitly requires no LLM involvement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ── Keyword dictionaries ──────────────────────────────────────────────────────

_SEASON_KEYWORDS: dict[str, str] = {
    "kharif": "kharif",
    "खरीफ": "kharif",
    "rabi": "rabi",
    "रबी": "rabi",
    "zaid": "zaid",
    "jayad": "zaid",
    "perennial": "perennial",
}

_CROP_KEYWORDS: list[str] = [
    "rice", "wheat", "maize", "corn", "cotton", "sugarcane", "soybean",
    "groundnut", "tomato", "potato", "onion", "mustard", "sorghum",
    "bajra", "jowar", "tur", "arhar", "chickpea", "gram", "lentil",
    "sunflower", "sesame", "jute", "tobacco", "rubber", "coconut",
    "mango", "banana", "grape", "papaya", "guava", "pomegranate",
    "turmeric", "ginger", "chilli", "pepper", "cardamom",
    # Hindi names
    "गेहूं", "धान", "मक्का", "कपास", "सरसों", "मूंगफली",
]

_LANGUAGE_PATTERNS: dict[str, re.Pattern] = {
    "hi": re.compile(r"[\u0900-\u097F]"),     # Devanagari
    "ta": re.compile(r"[\u0B80-\u0BFF]"),     # Tamil
    "te": re.compile(r"[\u0C00-\u0C7F]"),     # Telugu
    "kn": re.compile(r"[\u0C80-\u0CFF]"),     # Kannada
    "ml": re.compile(r"[\u0D00-\u0D7F]"),     # Malayalam
    "mr": re.compile(r"[\u0900-\u097F]"),     # Marathi (also Devanagari)
    "bn": re.compile(r"[\u0980-\u09FF]"),     # Bengali
    "gu": re.compile(r"[\u0A80-\u0AFF]"),     # Gujarati
    "pa": re.compile(r"[\u0A00-\u0A7F]"),     # Punjabi / Gurmukhi
}


# ── Result dataclass ──────────────────────────────────────────────────────────


@dataclass(slots=True)
class ExtractedMetadata:
    """Heuristically derived metadata from document content.

    Fields remain None when detection fails or text is insufficient.
    Upload-time metadata (from DocumentUploadMetadata) overrides these.
    """

    detected_language: str | None = None
    detected_crop: str | None = None
    detected_season: str | None = None
    confidence_notes: list[str] = field(default_factory=list)


# ── Extractor ─────────────────────────────────────────────────────────────────


class MetadataExtractor:
    """Heuristic keyword-based agricultural metadata extractor.

    Usage
    -----
    extractor = MetadataExtractor()
    result = extractor.extract(full_text)
    """

    # Use only the first N characters for fast heuristic scanning.
    _SCAN_LIMIT = 5_000

    def extract(self, text: str) -> ExtractedMetadata:
        """Run all heuristics over the provided text.

        Parameters
        ----------
        text:
            Cleaned full document text (concatenation of all pages).

        Returns
        -------
        ExtractedMetadata
            Heuristically derived fields with confidence notes.
        """
        sample = text[: self._SCAN_LIMIT].lower()
        result = ExtractedMetadata()

        result.detected_language = self._detect_language(text)
        result.detected_season = self._detect_season(sample)
        result.detected_crop = self._detect_crop(sample)

        return result

    # ── Internal heuristics ───────────────────────────────────────────────

    def _detect_language(self, text: str) -> str:
        """Return BCP-47 code of the dominant non-Latin script, or 'en'."""
        counts: dict[str, int] = {}
        for lang, pattern in _LANGUAGE_PATTERNS.items():
            matches = pattern.findall(text[: self._SCAN_LIMIT])
            if matches:
                counts[lang] = len(matches)

        if not counts:
            return "en"

        # Pick the language with the most characters (simple heuristic)
        dominant = max(counts, key=lambda k: counts[k])
        # Disambiguate Devanagari: hi vs mr is contextual — default to hi
        if dominant == "mr" and counts.get("hi", 0) >= counts.get("mr", 0):
            return "hi"
        return dominant

    def _detect_season(self, sample: str) -> str | None:
        """Scan for season keyword matches."""
        for keyword, canonical in _SEASON_KEYWORDS.items():
            if keyword in sample:
                return canonical
        return None

    def _detect_crop(self, sample: str) -> str | None:
        """Return the first matching crop keyword found in the text."""
        for crop in _CROP_KEYWORDS:
            if crop in sample:
                return crop
        return None
