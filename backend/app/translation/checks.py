"""Post-translation safety checks (block publication on failure).

The checks are independent of how a translation was produced (machine, LLM or officer
edit). They verify that every number, unit and protected term in the source survives in
the translation:

* digits in Devanagari (०-९) and Telugu (౦-౯) are normalised to ASCII;
* Indian digit grouping ("1,50,000") and western grouping ("150,000") both parse;
* units are matched by their en/hi/te spellings from the agri glossary;
* protected terms (active ingredients, formulation codes, schemes, agencies) must appear
  verbatim.

Limitation: numbers written as words ("two sprays") are not detected. Advisories normally
use digits for doses, and reviewers see the side-by-side text.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation

from app.translation.glossary import Glossary, get_glossary

_DIGIT_MAP = {**{0x0966 + i: str(i) for i in range(10)}, **{0x0C66 + i: str(i) for i in range(10)}}
# Digits glued to Latin identifiers (e.g. "H2O", "v1.2") are not quantities; digits after
# Indic letters still are, because Telugu/Hindi text often omits the space before numbers.
_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_.])\d+(?:,\d{2,3})*(?:\.\d+)?(?!\d)")
# Any placeholder form an MT model may emit: <3>, [3], {3}, ⟦3⟧, [[3]], <ID3>; digits may come
# back in Devanagari/Telugu numerals (Python's \d matches them).
PLACEHOLDER_RE = re.compile(r"[\[⟦<{]{1,2}\s*(?:PH|ph|ID)?\s*(\d+)\s*[\]⟧>}]{1,2}")


def normalize_digits(text: str) -> str:
    """Map Devanagari and Telugu digits to ASCII digits."""
    return text.translate(_DIGIT_MAP)


def _canonical_number(raw: str) -> str:
    try:
        value = Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return raw
    normalized = value.normalize()
    return format(normalized, "f")


def extract_numbers(text: str) -> Counter[str]:
    """Multiset of canonical numbers in ``text`` (any of the three digit systems)."""
    text = PLACEHOLDER_RE.sub(" ", normalize_digits(text))
    return Counter(_canonical_number(m.group(0)) for m in _NUMBER_RE.finditer(text))


_PATTERN_CACHE: dict[str, list[tuple[re.Pattern[str], str]]] = {}


def _unit_patterns(glossary: Glossary) -> list[tuple[re.Pattern[str], str]]:
    cached = _PATTERN_CACHE.get(glossary.version)
    if cached is not None:
        return cached
    pairs: list[tuple[str, str]] = sorted(
        glossary.unit_lookup().items(), key=lambda kv: len(kv[0]), reverse=True
    )
    patterns: list[tuple[re.Pattern[str], str]] = []
    for spelling, canonical in pairs:
        escaped = re.escape(spelling)
        if spelling.isascii() and spelling[-1].isalpha():
            regex = rf"(?<![A-Za-z]){escaped}(?![A-Za-z])"
        else:  # symbols, and Indic spellings (which may carry inflectional suffixes)
            regex = escaped
        patterns.append((re.compile(regex, re.IGNORECASE), canonical))
    _PATTERN_CACHE[glossary.version] = patterns
    return patterns


def extract_units(text: str, glossary: Glossary | None = None) -> Counter[str]:
    """Multiset of canonical units, longest spelling first, without overlaps."""
    glossary = glossary or get_glossary()
    remaining = normalize_digits(text)
    found: Counter[str] = Counter()
    for pattern, canonical in _unit_patterns(glossary):
        def _consume(m: re.Match[str], unit: str = canonical) -> str:
            found[unit] += 1
            return " " * len(m.group(0))

        remaining = pattern.sub(_consume, remaining)
    return found


def _protected_in(text: str, glossary: Glossary) -> Counter[str]:
    found: Counter[str] = Counter()
    for term in glossary.protected_terms:
        pattern = rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])"
        flags = 0 if term.isupper() else re.IGNORECASE  # 'SC' must not match 'sc' in words
        n = len(re.findall(pattern, text, flags))
        if n:
            found[term.casefold()] += n
    return found


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Outcome of the safety checks. ``passed`` gates publication."""

    passed: bool
    missing_numbers: list[str] = field(default_factory=list)
    extra_numbers: list[str] = field(default_factory=list)
    missing_units: list[str] = field(default_factory=list)
    extra_units: list[str] = field(default_factory=list)
    missing_protected_terms: list[str] = field(default_factory=list)
    leftover_placeholders: list[str] = field(default_factory=list)
    numbers_in_source: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def reasons(self) -> list[str]:
        out = []
        if self.missing_numbers:
            out.append(f"missing numbers {self.missing_numbers}")
        if self.extra_numbers:
            out.append(f"unexpected numbers {self.extra_numbers}")
        if self.missing_units:
            out.append(f"missing units {self.missing_units}")
        if self.missing_protected_terms:
            out.append(f"missing protected terms {self.missing_protected_terms}")
        if self.leftover_placeholders:
            out.append(f"unrestored placeholders {self.leftover_placeholders}")
        return out


def _expand(counter: Counter[str]) -> list[str]:
    return sorted(counter.elements())


def check_translation(source: str, translation: str,
                      glossary: Glossary | None = None) -> CheckResult:
    """Compare source and translation. Missing or extra numbers, missing units, missing
    protected terms and leftover placeholders all fail. Extra units are reported only."""
    glossary = glossary or get_glossary()
    src_n, tgt_n = extract_numbers(source), extract_numbers(translation)
    src_u, tgt_u = extract_units(source, glossary), extract_units(translation, glossary)
    src_p, tgt_p = _protected_in(source, glossary), _protected_in(translation, glossary)
    leftovers = [m.group(0) for m in PLACEHOLDER_RE.finditer(translation)]
    result = CheckResult(
        passed=False,
        missing_numbers=_expand(src_n - tgt_n),
        extra_numbers=_expand(tgt_n - src_n),
        missing_units=_expand(src_u - tgt_u),
        extra_units=_expand(tgt_u - src_u),
        missing_protected_terms=_expand(src_p - tgt_p),
        leftover_placeholders=leftovers,
        numbers_in_source=sum(src_n.values()),
    )
    passed = not (result.missing_numbers or result.extra_numbers or result.missing_units
                  or result.missing_protected_terms or result.leftover_placeholders)
    return CheckResult(**{**result.to_dict(), "passed": passed})
