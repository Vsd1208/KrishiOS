"""Mask spans that must not be altered by machine translation, then restore them.

Masked span kinds:

* ``quantity``: a number or range with its unit ("0.6 g/L", "2-3 days" keeps only the
  numbers, "75%", "25 kg per acre"). Restored verbatim (Latin digits and units are standard
  in official te/hi advisories).
* ``protected``: glossary terms (active ingredients, formulation codes, schemes, agencies).
  Restored verbatim.
* ``crop``: an English crop name from the shared catalog. Restored as the catalog name in the
  target language, so crop terminology is consistent across all translations.

The placeholder token is configurable because MT models differ in which tokens they copy
through unchanged; the Phase 2 evaluation measures placeholder survival per provider.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.catalog import get_crop_catalog
from app.translation.checks import PLACEHOLDER_RE, normalize_digits
from app.translation.glossary import Glossary, get_glossary

# "<i>" chosen empirically: copied through opus-mt en->hi 11/11 and en->te 10/11 in the Phase 2
# probe, versus 5/11 for "[i]" (ml/reports/02_multilingual_core.md).
DEFAULT_PLACEHOLDER = "<{i}>"
_RESTORE_RE = PLACEHOLDER_RE
MIN_CROP_ALIAS_LEN = 3  # skip 2-letter aliases; too ambiguous inside English text
_NUM = r"\d+(?:,\d{2,3})*(?:\.\d+)?"


@dataclass(frozen=True, slots=True)
class Span:
    index: int
    kind: str  # quantity | protected | crop
    source: str
    replacement: str


@dataclass(slots=True)
class Masked:
    text: str
    spans: list[Span] = field(default_factory=list)


def _unit_alternation(glossary: Glossary, latin_only: bool) -> str:
    spellings = sorted(
        {s for s in glossary.unit_lookup() if (s.isascii() or not latin_only)},
        key=len, reverse=True,
    )
    return "|".join(re.escape(s) for s in spellings)


class Protector:
    """Masks protected spans for one (source, target) language pair."""

    def __init__(self, glossary: Glossary | None = None,
                 placeholder: str = DEFAULT_PLACEHOLDER) -> None:
        self._glossary = glossary or get_glossary()
        self._placeholder = placeholder
        self._catalog = get_crop_catalog()

    def _quantity_re(self, source_language: str) -> re.Pattern[str]:
        units = _unit_alternation(self._glossary, latin_only=source_language == "en")
        unit = rf"(?:{units})(?![A-Za-z])"
        per = rf"(?:\s*/\s*{unit}|\s+per\s+{unit})?"
        rng = rf"(?:\s*(?:-|–|to)\s*{_NUM})?"
        return re.compile(
            rf"(?<![A-Za-z0-9_.\[⟦<{{]){_NUM}{rng}(?:\s*{unit}{per})?(?![\]⟧>}}])",
            re.IGNORECASE,
        )

    def _protected_re(self) -> list[re.Pattern[str]]:
        out = []
        for term in sorted(self._glossary.protected_terms, key=len, reverse=True):
            flags = 0 if term.isupper() else re.IGNORECASE
            out.append(re.compile(rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])", flags))
        return out

    def _crop_patterns(self, target_language: str) -> list[tuple[re.Pattern[str], str]]:
        ambiguous = set(self._catalog.ambiguous_aliases())
        pairs: list[tuple[str, str]] = []
        for entry in self._catalog.entries():
            target_name = entry.display_name(target_language)
            for name in (entry.name_en.split("(")[0].strip(), *entry.aliases):
                if (name.isascii() and name.casefold() not in ambiguous
                        and len(name) >= MIN_CROP_ALIAS_LEN):
                    pairs.append((name, target_name))
        pairs.sort(key=lambda p: len(p[0]), reverse=True)
        return [
            (re.compile(rf"(?<![A-Za-z]){re.escape(n)}(?:s|es)?(?![A-Za-z])", re.IGNORECASE), t)
            for n, t in pairs
        ]

    def mask(self, text: str, source_language: str, target_language: str,
             map_crops: bool = True) -> Masked:
        """Replace protected spans with indexed placeholders."""
        masked = Masked(text=normalize_digits(text))
        # Quantities first: later passes only see placeholders without letters, and the
        # quantity pass never sees placeholder digits.
        passes: list[tuple[str, list[tuple[re.Pattern[str], str | None]]]] = [
            ("quantity", [(self._quantity_re(source_language), None)]),
            ("protected", [(p, None) for p in self._protected_re()]),
        ]
        if map_crops and source_language == "en" and target_language != "en":
            passes.append(("crop", list(self._crop_patterns(target_language))))

        for kind, patterns in passes:
            for pattern, target_value in patterns:
                def _sub(m: re.Match[str], k: str = kind, tv: str | None = target_value) -> str:
                    if _RESTORE_RE.fullmatch(m.group(0)):
                        return m.group(0)
                    idx = len(masked.spans)
                    masked.spans.append(Span(idx, k, m.group(0), tv or m.group(0)))
                    return self._placeholder.format(i=idx)

                masked.text = pattern.sub(_sub, masked.text)
        return masked

    @staticmethod
    def restore(translated: str, spans: list[Span]) -> tuple[str, list[int]]:
        """Put spans back. Returns (text, indices of placeholders that went missing)."""
        by_index = {s.index: s for s in spans}
        seen: set[int] = set()

        def _sub(m: re.Match[str]) -> str:
            idx = int(m.group(1))
            span = by_index.get(idx)
            if span is None:
                return m.group(0)  # leave it; the checker reports leftovers
            seen.add(idx)
            return span.replacement

        restored = _RESTORE_RE.sub(_sub, translated)
        missing = sorted(set(by_index) - seen)
        return restored, missing
