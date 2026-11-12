"""Script-aware text normalisation shared by catalog, NLU and translation checks."""

from __future__ import annotations

import re
import unicodedata

# Token characters: letters, combining marks (Indic matras/virama), digits.
_TOKEN_RE = re.compile(r"[\wऀ-ॿఀ-౿]+", re.UNICODE)


def normalize(text: str) -> str:
    """NFC-normalise, casefold, map punctuation to spaces and collapse whitespace."""
    text = unicodedata.normalize("NFC", text).casefold()
    return " ".join(tokenize(text))


def tokenize(text: str) -> list[str]:
    """Split into tokens that keep Indic combining marks attached to their letters."""
    return _TOKEN_RE.findall(unicodedata.normalize("NFC", text).casefold())


_TELUGU = (0x0C00, 0x0C7F)
_DEVANAGARI = (0x0900, 0x097F)


def script_of(token: str) -> str:
    """Dominant script of a token: 'telugu', 'devanagari', 'latin' or 'other'."""
    counts = {"telugu": 0, "devanagari": 0, "latin": 0}
    for ch in token:
        cp = ord(ch)
        if _TELUGU[0] <= cp <= _TELUGU[1]:
            counts["telugu"] += 1
        elif _DEVANAGARI[0] <= cp <= _DEVANAGARI[1]:
            counts["devanagari"] += 1
        elif ch.isascii() and ch.isalpha():
            counts["latin"] += 1
    best = max(counts, key=counts.__getitem__)
    return best if counts[best] else "other"


def is_indic(token: str) -> bool:
    return script_of(token) in {"telugu", "devanagari"}
