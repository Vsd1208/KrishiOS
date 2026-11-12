"""Generic multilingual phrase matcher (same matching rules as the crop resolver).

* Latin phrases match whole tokens (optional plural ``s`` on the last token).
* Telugu/Devanagari phrases may carry up to ``MAX_INDIC_SUFFIX`` characters of inflection
  on their last token (``వర్షాలు``, ``తెగులుకు``, ``बारिश में``).
* Longest match first, no overlaps.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.catalog.text import is_indic, tokenize

MAX_INDIC_SUFFIX = 4
MIN_INDIC_STEM = 2
MIN_PLURAL_LEN = 4


@dataclass(frozen=True, slots=True)
class PhraseHit:
    label: str
    phrase: str
    token_start: int
    token_end: int


class PhraseMatcher:
    """Maps phrases (any script) to labels."""

    def __init__(self, entries: Iterable[tuple[str, str]]) -> None:
        self._index: dict[tuple[str, ...], set[str]] = {}
        for label, phrase in entries:
            toks = tuple(tokenize(phrase))
            if toks:
                self._index.setdefault(toks, set()).add(label)
        self._max_len = max((len(k) for k in self._index), default=1)

    def phrases(self) -> list[str]:
        """All indexed phrases (normalised, space-joined)."""
        return [" ".join(k) for k in self._index]

    def _lookup(self, window: list[str]) -> tuple[tuple[str, ...], set[str]] | None:
        exact = tuple(window)
        if exact in self._index:
            return exact, self._index[exact]
        *head, last = window
        if last.isascii() and last.endswith("s") and len(last) >= MIN_PLURAL_LEN:
            key = (*head, last[:-1])
            if key in self._index:
                return key, self._index[key]
        if is_indic(last):
            for cut in range(1, MAX_INDIC_SUFFIX + 1):
                stem = last[:-cut]
                key = (*head, stem)
                if len(stem) >= MIN_INDIC_STEM and key in self._index:
                    return key, self._index[key]
        return None

    def find(self, text: str) -> list[PhraseHit]:
        tokens = tokenize(text)
        hits: list[PhraseHit] = []
        i = 0
        while i < len(tokens):
            matched = False
            for length in range(min(self._max_len, len(tokens) - i), 0, -1):
                found = self._lookup(tokens[i : i + length])
                if found:
                    key, labels = found
                    hits.extend(
                        PhraseHit(label, " ".join(key), i, i + length) for label in sorted(labels)
                    )
                    i += length
                    matched = True
                    break
            if not matched:
                i += 1
        return hits
