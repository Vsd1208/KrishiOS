"""Multilingual crop resolver backed by ``ml/reference/crop_catalog.csv``.

Matching rules (deterministic, no fuzzy guessing):

* Aliases are normalised (NFC, casefold, punctuation removed) and matched on token
  sequences, longest alias first, without overlaps.
* Latin-script aliases must match whole tokens (an optional plural ``s`` is allowed).
* Telugu/Devanagari aliases may be followed by a short inflectional suffix on the last
  token (``వరికి`` = "to paddy", ``धान की``), up to ``MAX_INDIC_SUFFIX`` characters.
* An alias shared by several crops (e.g. "gobhi") yields an AMBIGUOUS resolution so the
  UI shows a crop picker; the system never silently chooses one.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from loguru import logger

from app.catalog.paths import reference_dir
from app.catalog.text import is_indic, normalize, tokenize

MAX_INDIC_SUFFIX = 4
MIN_PLURAL_LEN = 4  # only strip a plural 's' from Latin tokens of 4+ letters
MIN_INDIC_STEM = 2


@dataclass(frozen=True, slots=True)
class CropEntry:
    """One crop from the shared catalog."""

    crop_canonical: str
    name_en: str
    name_te: str
    name_hi: str
    aliases: tuple[str, ...]
    scientific_name: str
    crop_group: str
    domain: str
    seasons: tuple[str, ...]
    yield_unit: str
    apy_names: tuple[str, ...]
    tier: str
    vision_supported: bool
    review_status: str

    def display_name(self, language: str) -> str:
        """Name in the farmer's language (falls back to English)."""
        return {"te": self.name_te, "hi": self.name_hi}.get(language) or self.name_en


class ResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    MULTIPLE = "multiple"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class CropMention:
    """A span of the input that matched one or more catalog crops."""

    surface: str
    alias: str
    candidates: tuple[str, ...]
    token_start: int
    token_end: int


@dataclass(frozen=True, slots=True)
class CropResolution:
    """Result of resolving free text to catalog crops."""

    status: ResolutionStatus
    crop: str | None
    candidates: tuple[str, ...]
    mentions: tuple[CropMention, ...] = field(default_factory=tuple)


def _split(value: str) -> tuple[str, ...]:
    return tuple(v.strip() for v in value.split("|") if v.strip())


def _name_variants(name_en: str) -> list[str]:
    """'Pigeon pea (Tur/Arhar)' -> ['Pigeon pea (Tur/Arhar)', 'Pigeon pea', 'Tur', 'Arhar']."""
    variants = [name_en]
    if "(" in name_en:
        head, _, rest = name_en.partition("(")
        variants.append(head.strip())
        variants.extend(p.strip() for p in rest.rstrip(")").split("/"))
    return [v for v in variants if v]


class CropCatalog:
    """In-memory catalog with an alias index for resolution."""

    def __init__(self, entries: list[CropEntry]) -> None:
        self._entries = {e.crop_canonical: e for e in entries}
        self._index: dict[tuple[str, ...], set[str]] = {}
        for entry in entries:
            names = [
                entry.crop_canonical.replace("_", " "),
                *_name_variants(entry.name_en),
                entry.name_te,
                entry.name_hi,
                *entry.aliases,
            ]
            for name in names:
                tokens = tuple(tokenize(name))
                if tokens:
                    self._index.setdefault(tokens, set()).add(entry.crop_canonical)
        self._max_len = max((len(k) for k in self._index), default=1)

    # ── lookup ──────────────────────────────────────────────────────────────
    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, crop_canonical: object) -> bool:
        return crop_canonical in self._entries

    def get(self, crop_canonical: str) -> CropEntry | None:
        return self._entries.get(crop_canonical)

    def entries(self) -> list[CropEntry]:
        return list(self._entries.values())

    def ambiguous_aliases(self) -> dict[str, list[str]]:
        return {" ".join(k): sorted(v) for k, v in self._index.items() if len(v) > 1}

    # ── matching ────────────────────────────────────────────────────────────
    def _match_at(self, tokens: list[str], i: int) -> tuple[int, tuple[str, ...]] | None:
        """Longest alias starting at token ``i``; returns (length, alias tokens)."""
        for length in range(min(self._max_len, len(tokens) - i), 0, -1):
            window = tokens[i : i + length]
            for alias in self._candidates_for_window(window):
                return length, alias
        return None

    def _candidates_for_window(self, window: list[str]) -> list[tuple[str, ...]]:
        exact = tuple(window)
        if exact in self._index:
            return [exact]
        *head, last = window
        found: list[tuple[str, ...]] = []
        if last.isascii() and last.endswith("s") and len(last) >= MIN_PLURAL_LEN:
            plural = (*head, last[:-1])
            if plural in self._index:
                found.append(plural)
        if is_indic(last):
            for cut in range(1, MAX_INDIC_SUFFIX + 1):
                stem = last[:-cut]
                if len(stem) >= MIN_INDIC_STEM and (*head, stem) in self._index:
                    found.append((*head, stem))
                    break
        return found

    def find_mentions(self, text: str) -> list[CropMention]:
        """All non-overlapping crop mentions, longest match first."""
        tokens = tokenize(text)
        mentions: list[CropMention] = []
        i = 0
        while i < len(tokens):
            hit = self._match_at(tokens, i)
            if hit is None:
                i += 1
                continue
            length, alias = hit
            mentions.append(
                CropMention(
                    surface=" ".join(tokens[i : i + length]),
                    alias=" ".join(alias),
                    candidates=tuple(sorted(self._index[alias])),
                    token_start=i,
                    token_end=i + length,
                )
            )
            i += length
        return mentions

    def resolve(self, text: str) -> CropResolution:
        """Resolve free text to a single crop, or explain why it cannot."""
        mentions = tuple(self.find_mentions(text))
        if not mentions:
            return CropResolution(ResolutionStatus.NOT_FOUND, None, (), mentions)
        ambiguous = [m for m in mentions if len(m.candidates) > 1]
        distinct = sorted({c for m in mentions for c in m.candidates})
        definite = sorted({m.candidates[0] for m in mentions if len(m.candidates) == 1})
        if ambiguous and not definite:
            return CropResolution(ResolutionStatus.AMBIGUOUS, None, tuple(distinct), mentions)
        if len(definite) == 1 and all(definite[0] in m.candidates for m in mentions):
            return CropResolution(ResolutionStatus.RESOLVED, definite[0], (definite[0],), mentions)
        return CropResolution(ResolutionStatus.MULTIPLE, None, tuple(distinct), mentions)

    def resolve_name(self, name: str) -> str | None:
        """Exact lookup of a single crop name/alias (used for structured inputs)."""
        tokens = tuple(tokenize(name))
        matches = self._index.get(tokens, set())
        if len(matches) == 1:
            return next(iter(matches))
        canonical = normalize(name).replace(" ", "_")
        return canonical if canonical in self._entries else None


def load_crop_catalog(path: Path) -> CropCatalog:
    """Parse the catalog CSV (validation lives in ``ml``; here we fail on missing fields)."""
    entries: list[CropEntry] = []
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            entries.append(
                CropEntry(
                    crop_canonical=row["crop_canonical"].strip(),
                    name_en=row["name_en"].strip(),
                    name_te=row["name_te"].strip(),
                    name_hi=row["name_hi"].strip(),
                    aliases=_split(row["aliases"]),
                    scientific_name=row["scientific_name"].strip(),
                    crop_group=row["crop_group"].strip(),
                    domain=row["domain"].strip(),
                    seasons=_split(row["seasons"]),
                    yield_unit=row["yield_unit"].strip(),
                    apy_names=_split(row["apy_names"]),
                    tier=row["tier"].strip(),
                    vision_supported=row["vision_supported"].strip().lower() == "true",
                    review_status=row["review_status"].strip(),
                )
            )
    logger.info("Crop catalog loaded | crops={} | path={}", len(entries), path)
    return CropCatalog(entries)


@lru_cache(maxsize=1)
def get_crop_catalog() -> CropCatalog:
    """Process-wide catalog singleton."""
    return load_crop_catalog(reference_dir() / "crop_catalog.csv")
