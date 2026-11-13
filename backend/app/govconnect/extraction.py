"""Structured extraction of a government bulletin (rules-v1), with provenance.

Every extracted value carries the character spans of the source text it came from, so the
officer review screen can highlight them and nothing appears that the source did not say.
Fields below ``REVIEW_THRESHOLD`` confidence are listed in ``low_confidence``; uploads always
go to officer review before publication regardless.

The extractor is deliberately deterministic and local (bulletin text may be pasted with
farmer context; no data leaves the device). An LLM extractor can implement the same
``BulletinExtractor`` protocol later and be compared on the same labelled set.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

import yaml

from app.catalog.lgd import get_lgd_directory
from app.catalog.phrases import PhraseMatcher
from app.catalog.resolver import get_crop_catalog
from app.catalog.text import script_of, tokenize

EXTRACTOR_NAME = "rules-v1"
REVIEW_THRESHOLD = 0.7
IST = timezone(timedelta(hours=5, minutes=30))
_TOKEN_RE = re.compile(r"[\wऀ-ॿఀ-౿]+", re.UNICODE)
_DISTRICT_WORDS = {"district", "districts", "dist", "zilla", "jila", "जिला", "जिले", "జిల్లా"}
_CUE_WINDOW = 90
_MAX_ACTIONS = 10
_TITLE_MAX = 120
_MONTHS = {
    m: i
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1
    )
}

_DATE_PATTERNS = [
    # "22:45, 10-11-2026": time first, as in IMD nowcasts
    (
        "hm_dmy",
        re.compile(
            r"\b(\d{1,2}):(\d{2})\s*(?:hrs|ist)?,?\s*(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b",
            re.IGNORECASE,
        ),
    ),
    ("ymd", re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")),
    ("dmy", re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4}|\d{2})\b")),
    ("d_mon_y", re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})\b")),
    ("mon_d_y", re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b")),
]
_TIME_RE = re.compile(r"^\s*(?:at\s*)?(\d{1,2})[:.](\d{2})\s*(hrs|hours|ist|am|pm)?", re.IGNORECASE)
_DURATION_RE = re.compile(
    r"\b(?:next|coming|following)\s+(?:\d{1,3}\s*(?:-|to)\s*)?(\d{1,3})\s*(hours|hrs|days)\b"
    r"|अगले\s+(\d{1,3})\s*(घंटे|घंटों|दिन|दिनों)"
    r"|రాబోయే\s+(\d{1,3})\s*(గంటల|గంటలు|రోజుల|రోజులు)",
    re.IGNORECASE,
)
_SENTENCE_RE = re.compile(r"[^\n.!?।]+[.!?।]?", re.UNICODE)


@dataclass(frozen=True, slots=True)
class Span:
    start: int
    end: int
    text: str


@dataclass(slots=True)
class ExtractedField:
    value: Any
    confidence: float
    spans: list[Span] = field(default_factory=list)


@dataclass(slots=True)
class BulletinExtraction:
    fields: dict[str, ExtractedField]
    ambiguous: dict[str, list[Any]] = field(default_factory=dict)
    extractor: str = EXTRACTOR_NAME

    @property
    def low_confidence(self) -> list[str]:
        return sorted(
            k
            for k, f in self.fields.items()
            if f.value not in (None, [], "") and f.confidence < REVIEW_THRESHOLD
        )

    def value(self, name: str, default: Any = None) -> Any:
        f = self.fields.get(name)
        return default if f is None or f.value in (None, []) else f.value

    def to_dict(self) -> dict[str, Any]:
        def enc(v: Any) -> Any:
            return v.isoformat() if isinstance(v, datetime) else v

        return {
            "extractor": self.extractor,
            "fields": {
                k: {
                    "value": enc(f.value),
                    "confidence": round(f.confidence, 2),
                    "spans": [asdict(s) for s in f.spans],
                }
                for k, f in self.fields.items()
            },
            "low_confidence": self.low_confidence,
            "ambiguous": self.ambiguous,
        }

    def provenance(self) -> dict[str, list[dict[str, Any]]]:
        return {k: [asdict(s) for s in f.spans] for k, f in self.fields.items() if f.spans}


class BulletinExtractor(Protocol):
    name: str

    def extract(self, text: str) -> BulletinExtraction: ...


@dataclass(frozen=True, slots=True)
class _Lexicon:
    hazards: PhraseMatcher
    severity: PhraseMatcher
    actions: PhraseMatcher
    authorities: PhraseMatcher
    authority_info: dict[str, tuple[str, str]]
    cues: dict[str, list[str]]


@lru_cache(maxsize=1)
def _lexicon() -> _Lexicon:
    data = yaml.safe_load((Path(__file__).with_name("lexicon.yaml")).read_text(encoding="utf-8"))

    def pairs(section: dict[str, dict[str, list[str]]]) -> list[tuple[str, str]]:
        return [
            (label, p)
            for label, langs in section.items()
            for phrases in langs.values()
            for p in phrases
        ]

    auth = data["authorities"]
    return _Lexicon(
        hazards=PhraseMatcher(pairs(data["hazards"])),
        severity=PhraseMatcher(pairs(data["severity"])),
        actions=PhraseMatcher(
            [("action", p) for ps in data["action_markers"].values() for p in ps]
        ),
        authorities=PhraseMatcher([(str(i), a["phrase"]) for i, a in enumerate(auth)]),
        authority_info={str(i): (a["name"], a["level"]) for i, a in enumerate(auth)},
        cues={k: [" ".join(tokenize(c)) for c in v] for k, v in data["date_cues"].items()},
    )


def _offsets(text: str) -> list[tuple[int, int]]:
    return [m.span() for m in _TOKEN_RE.finditer(text)]


def _span(text: str, offs: list[tuple[int, int]], t0: int, t1: int) -> Span:
    start, end = offs[t0][0], offs[t1 - 1][1]
    return Span(start, end, text[start:end])


def _language(text: str) -> ExtractedField:
    scripts = [script_of(t) for t in tokenize(text)]
    te, hi, lat = scripts.count("telugu"), scripts.count("devanagari"), scripts.count("latin")
    total = max(te + hi + lat, 1)
    lang = "te" if te >= max(hi, 1) and te >= lat else "hi" if hi >= max(lat, 1) else "en"
    share = {"te": te, "hi": hi, "en": lat}[lang] / total
    return ExtractedField(lang, round(min(1.0, 0.5 + share / 2), 2))


def _title(text: str) -> ExtractedField:
    pos = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped:
            start = pos + line.index(stripped)
            value = stripped[:300]
            if len(value) > _TITLE_MAX:  # a paragraph, not a headline: keep its first clause
                cut = re.search(r"[.:!?।]\s", value)
                value = value[: cut.start() + 1] if cut and cut.start() >= 8 else value[:_TITLE_MAX]  # noqa: PLR2004
            return ExtractedField(value, 0.6, [Span(start, start + len(value), value)])
        pos += len(line)
    return ExtractedField(None, 0.0)


def _authority(text: str, offs: list[tuple[int, int]]) -> tuple[ExtractedField, ExtractedField]:
    lex = _lexicon()
    hits = lex.authorities.find(text)
    if not hits:
        return ExtractedField(None, 0.0), ExtractedField(None, 0.0)
    best = min(hits, key=lambda h: int(h.label))  # lexicon order = priority
    name, level = lex.authority_info[best.label]
    span = _span(text, offs, best.token_start, best.token_end)
    return ExtractedField(name, 0.8, [span]), ExtractedField(level, 0.7, [span])


def _labelled(
    text: str, offs: list[tuple[int, int]], matcher: PhraseMatcher, ranking: list[str] | None = None
) -> ExtractedField:
    hits = matcher.find(text)
    if not hits:
        return ExtractedField(None, 0.0)
    counts: dict[str, list[Span]] = {}
    for h in hits:
        counts.setdefault(h.label, []).append(_span(text, offs, h.token_start, h.token_end))
    if ranking:  # most severe wins
        label = next(r for r in ranking if r in counts)
    else:  # first mentioned is primary (titles and headlines lead with the main hazard)
        label = min(counts, key=lambda k: counts[k][0].start)
    confidence = 0.9 if len(counts) == 1 else 0.6
    return ExtractedField(label, confidence, counts[label])


def _parse_date(kind: str, groups: tuple[str, ...]) -> datetime | None:
    try:
        if kind == "hm_dmy":
            hh, mm, d, m, y = (int(g) for g in groups)
            return datetime(y, m, d, hh, mm, tzinfo=IST)
        if kind == "ymd":
            y, m, d = (int(g) for g in groups)
        elif kind == "dmy":
            d, m, y = int(groups[0]), int(groups[1]), int(groups[2])
            y += 2000 if y < 100 else 0  # noqa: PLR2004 - two-digit years
        elif kind == "d_mon_y":
            d, m, y = int(groups[0]), _MONTHS.get(groups[1][:3].lower(), 0), int(groups[2])
        else:
            m, d, y = _MONTHS.get(groups[0][:3].lower(), 0), int(groups[1]), int(groups[2])
        return datetime(y, m, d, tzinfo=IST)
    except (ValueError, TypeError):
        return None


@dataclass(slots=True)
class _DateHit:
    when: datetime
    span: Span
    cue: str | None


def _dates(text: str) -> list[_DateHit]:
    lex = _lexicon()
    taken: list[tuple[int, int]] = []
    hits: list[_DateHit] = []
    for kind, rx in _DATE_PATTERNS:
        for m in rx.finditer(text):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            when = _parse_date(kind, m.groups())
            if when is None:
                continue
            end = m.end()
            t = _TIME_RE.match(text[end : end + 20])
            if t:
                hour, minute = int(t.group(1)), int(t.group(2))
                suffix = (t.group(3) or "").lower()
                hour += 12 if suffix == "pm" and hour < 12 else 0  # noqa: PLR2004
                hour = 0 if suffix == "am" and hour == 12 else hour  # noqa: PLR2004
                if hour < 24 and minute < 60:  # noqa: PLR2004
                    when = when.replace(hour=hour, minute=minute)
                    end += t.end()
            taken.append((m.start(), end))
            line_start = text.rfind("\n", 0, m.start()) + 1
            before = " ".join(tokenize(text[max(line_start, m.start() - _CUE_WINDOW) : m.start()]))
            after = " ".join(tokenize(text[end : end + 12]))
            cue = None
            nearest = -1
            padded = f" {before} "
            for name in ("issued", "valid_to", "valid_from"):
                for c in lex.cues[name]:
                    pos = padded.rfind(f" {c} ")
                    if pos > nearest:  # the cue closest to the date wins
                        nearest, cue = pos, name
            if cue is None and any(after.startswith(c) for c in lex.cues["valid_to"]):
                cue = "valid_to"  # Hindi/Telugu postposition: "<date> तक" / "<date> వరకు"
            hits.append(_DateHit(when, Span(m.start(), end, text[m.start() : end]), cue))
    return sorted(hits, key=lambda h: h.span.start)


def _validity(text: str) -> dict[str, ExtractedField]:
    hits = _dates(text)
    by_cue = {h.cue: h for h in reversed(hits) if h.cue}
    out: dict[str, ExtractedField] = {}
    issued = by_cue.get("issued") or (hits[0] if hits else None)
    out["issued_at"] = (
        ExtractedField(issued.when, 0.9 if issued.cue else 0.5, [issued.span])
        if issued
        else ExtractedField(None, 0.0)
    )
    frm = by_cue.get("valid_from")
    out["valid_from"] = (
        ExtractedField(frm.when, 0.9, [frm.span])
        if frm
        else ExtractedField(issued.when, 0.5, [issued.span])
        if issued
        else ExtractedField(None, 0.0)
    )
    until = by_cue.get("valid_to")
    if until:
        when = until.when
        if when.hour == 0 and when.minute == 0:
            when = when.replace(hour=23, minute=59)  # "valid till 14.11.2026" = end of day
        out["valid_to"] = ExtractedField(when, 0.9, [until.span])
        return out
    m = _DURATION_RE.search(text)
    base = out["valid_from"].value
    if m and base is not None:
        n_str, unit = next((m.group(i), m.group(i + 1)) for i in (1, 3, 5) if m.group(i))
        hours = int(n_str) * (24 if unit.lower() in {"days", "दिन", "दिनों", "రోజుల", "రోజులు"} else 1)
        span = Span(m.start(), m.end(), text[m.start() : m.end()])
        out["valid_to"] = ExtractedField(
            base + timedelta(hours=hours), 0.7, [*out["valid_from"].spans, span]
        )
    elif len(hits) > 1 and issued is not None and hits[-1].when > issued.when:
        out["valid_to"] = ExtractedField(
            hits[-1].when.replace(hour=23, minute=59), 0.5, [hits[-1].span]
        )
    else:
        out["valid_to"] = ExtractedField(None, 0.0)
    return out


_DIRECTIONS = {"east", "west", "north", "south", "central"}


@lru_cache(maxsize=1)
def _district_index() -> tuple[PhraseMatcher, frozenset[str]]:
    """LGD district names plus spaceless spellings ("coochbehar") and the sourced alias file
    (``ml/reference/district_aliases.csv``). Labels: ``name:<LGD name>`` or ``code:<LGD code>``.
    Names that collide with ordinary words, or are pure compass directions (Delhi's "East"),
    only match next to a word for "district"."""
    import csv  # noqa: PLC0415

    from app.catalog.paths import reference_dir  # noqa: PLC0415
    from app.nlu.providers.rule_based import _district_matcher  # noqa: PLC0415

    _, collide = _district_matcher()
    pairs: list[tuple[str, str]] = []
    guarded = set(collide)
    for d in get_lgd_directory().districts():
        pairs.append((f"name:{d.district_name}", d.district_name))
        toks = tokenize(d.district_name)
        if len(toks) > 1:
            pairs.append((f"name:{d.district_name}", "".join(toks)))
        if toks and set(toks) <= _DIRECTIONS:
            guarded.add(" ".join(toks))
    alias_file = reference_dir() / "district_aliases.csv"
    if alias_file.exists():
        with alias_file.open(encoding="utf-8", newline="") as fh:
            pairs.extend(
                (f"code:{int(row['lgd_district_code'])}", row["alias"])
                for row in csv.DictReader(fh)
            )
    return PhraseMatcher(pairs), frozenset(guarded)


def _state_token_spans(tokens: list[str], states: set[str]) -> list[tuple[int, int]]:
    spans = []
    for state in states:
        st = state.split()
        for i in range(len(tokens) - len(st) + 1):
            if tokens[i : i + len(st)] == st:
                spans.append((i, i + len(st)))
    return spans


def _districts(  # noqa: PLR0912, PLR0915 - one pass over matches with guards
    text: str,
    offs: list[tuple[int, int]],
    issuer_ends: frozenset[int] = frozenset(),
) -> tuple[ExtractedField, ExtractedField, list[dict[str, Any]]]:
    """Districts named in the text. A place name right after an issuing office ("Meteorological
    Centre Hyderabad") is the issuer's location, not a target, and is skipped."""
    lgd = get_lgd_directory()
    matcher, collide = _district_index()
    tokens = tokenize(text)
    states = {" ".join(tokenize(d.state_name)) for d in lgd.districts()}
    norm_text = f" {' '.join(tokens)} "
    mentioned_states = {s for s in states if f" {s} " in norm_text}
    state_spans = _state_token_spans(tokens, mentioned_states)

    codes: list[int] = []
    spans: list[Span] = []
    ambiguous: list[dict[str, Any]] = []
    confidences: list[float] = []
    for hit in matcher.find(text):
        near = set(tokens[max(0, hit.token_start - 2) : hit.token_end + 2])
        if hit.phrase in collide and not near & _DISTRICT_WORDS:
            continue
        if set(hit.phrase.split()) <= _DIRECTIONS and (
            hit.token_end >= len(tokens) or tokens[hit.token_end] not in _DISTRICT_WORDS
        ):
            continue  # "East district" yes; "East Burdwan district" is not Delhi's East
        if hit.token_start in issuer_ends:
            continue
        if any(s <= hit.token_start and hit.token_end <= e for s, e in state_spans):
            continue  # "Jammu" inside "Jammu and Kashmir" is the state, not the district
        kind, _, value = hit.label.partition(":")
        if kind == "code":
            alias_target = lgd.district(int(value))
            candidates = [alias_target] if alias_target else []
        else:
            candidates = lgd.find_districts(value)
        if len(candidates) > 1 and mentioned_states:
            narrowed = [
                d for d in candidates if " ".join(tokenize(d.state_name)) in mentioned_states
            ]
            candidates = narrowed or candidates
        span = _span(text, offs, hit.token_start, hit.token_end)
        if len(candidates) == 1:
            code = candidates[0].lgd_district_code
            if code not in codes:
                codes.append(code)
            spans.append(span)
            confidences.append(0.9 if near & _DISTRICT_WORDS else 0.8)
        elif candidates:
            ambiguous.append(
                {
                    "text": span.text,
                    "start": span.start,
                    "end": span.end,
                    "candidates": [d.lgd_district_code for d in candidates],
                }
            )
    conf = min(confidences) if confidences else 0.0
    if ambiguous:
        conf = min(conf or 1.0, 0.5)
    districts = ExtractedField(codes, conf, spans)

    block_codes: list[int] = []
    block_spans: list[Span] = []
    if codes:
        blocks = [b for c in codes for b in lgd.blocks_of(c)]
        bm = PhraseMatcher([(str(b.lgd_block_code), b.block_name) for b in blocks])
        district_names = {
            " ".join(tokenize(lgd.district(c).district_name)) for c in codes if lgd.district(c)
        }
        for hit in bm.find(text):
            if hit.phrase in district_names:
                continue  # a block named like its district: the district match already covers it
            if int(hit.label) not in block_codes:
                block_codes.append(int(hit.label))
            block_spans.append(_span(text, offs, hit.token_start, hit.token_end))
    blocks_field = ExtractedField(block_codes, 0.7 if block_codes else 0.0, block_spans)
    return districts, blocks_field, ambiguous


def _crops(text: str, offs: list[tuple[int, int]]) -> tuple[ExtractedField, list[dict]]:
    keys: list[str] = []
    spans: list[Span] = []
    ambiguous: list[dict[str, Any]] = []
    for m in get_crop_catalog().find_mentions(text):
        span = _span(text, offs, m.token_start, m.token_end)
        if len(m.candidates) == 1:
            if m.candidates[0] not in keys:
                keys.append(m.candidates[0])
            spans.append(span)
        else:
            ambiguous.append(
                {
                    "text": span.text,
                    "start": span.start,
                    "end": span.end,
                    "candidates": list(m.candidates),
                }
            )
    return ExtractedField(keys, 0.85 if keys else 0.0, spans), ambiguous


def _actions(text: str) -> ExtractedField:
    lex = _lexicon()
    actions: list[str] = []
    spans: list[Span] = []
    for m in _SENTENCE_RE.finditer(text):
        sentence = m.group(0).strip(" \t-•*·")
        if len(sentence) < 8 or not lex.actions.find(sentence):  # noqa: PLR2004
            continue
        start = m.start() + m.group(0).index(sentence)
        actions.append(sentence)
        spans.append(Span(start, start + len(sentence), sentence))
        if len(actions) >= _MAX_ACTIONS:
            break
    return ExtractedField(actions, 0.6 if actions else 0.0, spans)


class RuleBasedBulletinExtractor:
    name = EXTRACTOR_NAME

    def extract(self, text: str) -> BulletinExtraction:
        text = unicodedata.normalize("NFC", text)
        offs = _offsets(text)
        if len(offs) != len(tokenize(text)):  # pragma: no cover - casefold changed tokens
            offs = []
        lex = _lexicon()
        authority, level = _authority(text, offs) if offs else (ExtractedField(None, 0.0),) * 2
        issuer_ends = frozenset(h.token_end for h in lex.authorities.find(text))
        districts, blocks, amb_d = (
            _districts(text, offs, issuer_ends)
            if offs
            else (ExtractedField([], 0.0), ExtractedField([], 0.0), [])
        )
        crops, amb_c = _crops(text, offs) if offs else (ExtractedField([], 0.0), [])
        hazard = _labelled(text, offs, lex.hazards) if offs else ExtractedField(None, 0.0)
        severity = _labelled(text, offs, lex.severity, ["CRITICAL", "HIGH", "MEDIUM"])
        if severity.value is None:
            # No colour code: a named hazard is at least MEDIUM, otherwise a LOW advisory.
            severity = ExtractedField("MEDIUM" if hazard.value else "LOW", 0.4)
        fields = {
            "title": _title(text),
            "original_language": _language(text),
            "authority": authority,
            "authority_level": level,
            **_validity(text),
            "district_codes": districts,
            "block_codes": blocks,
            "crops": crops,
            "hazard_type": hazard,
            "severity": severity,
            "recommended_actions": _actions(text),
        }
        ambiguous = {k: v for k, v in {"district_codes": amb_d, "crops": amb_c}.items() if v}
        others = sorted({h.label for h in lex.hazards.find(text)} - {hazard.value})
        if others:
            ambiguous["other_hazards"] = others
        return BulletinExtraction(fields=fields, ambiguous=ambiguous)


def as_utc(value: datetime | None) -> datetime | None:
    return value.astimezone(UTC) if value is not None else None


@lru_cache(maxsize=1)
def get_extractor() -> BulletinExtractor:
    return RuleBasedBulletinExtractor()
