"""Phase 10c: analyse an uploaded document for an officer (brief) or a farmer (plain summary).

- The file is parsed in memory (PDF, DOCX, TXT, image OCR) and never stored: a farmer's upload
  is personal data and is processed only on this machine (local parsers, on-device LLM, local
  translation).
- Officer brief: the deterministic GovConnect extractor (dates, places, crops, hazards, actions,
  each with its source span) plus an LLM summary in a fixed layout.
- Farmer summary: three plain sentences and "what to do", translated to the farmer's language.
- Long documents are summarised part by part, then combined. At most ``MAX_PARTS`` parts are
  read: the opening part plus, for a farmer, the parts that mention their crops or places most;
  ``parts_read`` / ``parts_total`` say how much was read.
- Safety checks: an output line is dropped and counted (``dropped_lines``) if it has a number
  the document does not contain, or attaches a specific product or disease to a crop that the
  document never mentions near it (so a dose cannot be invented or moved to another crop).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Literal

PART_CHARS = 6000
MAX_PARTS = 5  # longer documents: the opening part plus the parts most relevant to the farmer
MAX_CHARS = PART_CHARS * MAX_PARTS
Audience = Literal["officer", "farmer"]

PART_SYSTEM = (
    "You read part of an agricultural document. List its key facts as short bullet points. "
    "Copy every number, date, dose, unit and place name exactly as written. Do not add "
    "anything that is not in the text."
)
OFFICER_SYSTEM = (
    "You write briefs for agricultural officers from notes taken on a document. Use only the "
    "notes. Copy numbers, dates and doses exactly. If something is not in the notes, write "
    "'not stated'."
)
OFFICER_FORMAT = (
    "Write the brief with exactly these lines:\n"
    "Document type: <advisory | scheme or notification | weather warning | pest or disease "
    "alert | circular | other>\n"
    "Summary: <2-3 sentences>\n"
    "Key dates: <dates and deadlines>\n"
    "Who it concerns: <farmers, crops or groups affected; eligibility>\n"
    "Actions: <what officers or farmers must do>\n"
    "Places: <states, districts, villages>"
)
FARMER_SYSTEM = (
    "You explain documents to Indian farmers in simple words. Use only the notes. Copy "
    "numbers, dates and doses exactly. No technical jargon."
)
FARMER_FORMAT = (
    "Write:\nSummary: <three short, simple sentences>\nWhat to do:\n- <action>\n- <action>\n"
    "If the document asks nothing of farmers, write 'What to do: nothing'."
)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


@dataclass(slots=True)
class DocumentAnalysis:
    audience: str
    language: str
    text: str  # in ``language``, or English if translation_failed
    text_en: str
    extracted: dict[str, Any] = field(default_factory=dict)  # officer: structured fields
    pages: int = 0
    chars_read: int = 0
    truncated: bool = False  # True: some parts of the document were not read
    parts_read: int = 0
    parts_total: int = 0
    dropped_lines: int = 0
    translation_failed: bool = False
    model: str | None = None
    timings_ms: dict[str, float] = field(default_factory=dict)


def _numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in _NUMBER.findall(text)}


def keep_supported_lines(output: str, source: str) -> tuple[str, int]:
    """Drop lines containing a number that the source text does not contain."""
    known = _numbers(source)
    kept, dropped = [], 0
    for line in output.splitlines():
        if _numbers(line) - known:
            dropped += 1
            continue
        kept.append(line)
    return "\n".join(kept).strip(), dropped


_SYNONYMS = {"paddy": ["rice", "paddy"], "rice": ["rice", "paddy"], "maize": ["maize", "corn"],
             "chilli": ["chilli", "chili"], "redgram": ["redgram", "pigeonpea", "arhar"],
             "bengalgram": ["bengalgram", "chickpea", "gram"]}


@dataclass(slots=True)
class FarmerContext:
    """Where the farmer is and what they grow; focuses a summary on what applies to them."""

    crops: list[str] = field(default_factory=list)
    district: str | None = None
    state: str | None = None

    def terms(self) -> list[str]:
        out: list[str] = []
        for crop in self.crops:
            out += _SYNONYMS.get(crop.lower(), [crop.lower()])
        out += [x.lower() for x in (self.district, self.state) if x]
        return out

    def instruction(self) -> str:
        crops = ", ".join(self.crops) or "their crops"
        place = ", ".join(x for x in (self.district, self.state) if x) or "their area"
        return (f"This farmer grows {crops} in {place}. Give only the advice that applies to "
                "these crops and this place. If the notes say nothing about them, say so "
                "plainly in the summary.\n")


def select_parts(parts: list[str], terms: list[str], max_parts: int = MAX_PARTS) -> list[str]:
    """Parts to read: all if few; else the opening part plus those that mention the farmer's
    crops or places most (in document order), filled with the earliest parts if needed."""
    if len(parts) <= max_parts:
        return parts
    if not terms:
        return parts[:max_parts]

    def hits(part: str) -> int:
        low = part.lower()
        return sum(len(re.findall(r"\b" + re.escape(t) + r"\b", low)) for t in terms)

    scored = sorted(range(1, len(parts)), key=lambda i: hits(parts[i]), reverse=True)
    chosen = {0} | {i for i in scored[:max_parts - 1] if hits(parts[i]) > 0}
    for i in range(len(parts)):
        if len(chosen) >= max_parts:
            break
        chosen.add(i)
    return [parts[i] for i in sorted(chosen)]


# Crop names (and common synonyms) used to check that advice stays with its crop.
CROP_WORDS = {
    "paddy": ("paddy", "rice"), "rice": ("paddy", "rice"), "cotton": ("cotton",),
    "maize": ("maize", "corn"), "wheat": ("wheat",), "chilli": ("chilli", "chili"),
    "tomato": ("tomato",), "groundnut": ("groundnut",), "cowpea": ("cowpea",),
    "banana": ("banana",), "coconut": ("coconut",), "sugarcane": ("sugarcane",),
    "soybean": ("soybean",), "redgram": ("redgram", "pigeonpea", "arhar", "tur"),
    "onion": ("onion",), "brinjal": ("brinjal",), "okra": ("okra", "bhindi"),
    "mango": ("mango",), "turmeric": ("turmeric",), "mustard": ("mustard",),
    "sorghum": ("sorghum", "jowar"), "bajra": ("bajra", "pearl millet"),
    "blackgram": ("blackgram", "urd"), "greengram": ("greengram", "moong"),
}
NEAR_CHARS = 350  # how close a specific term must be to the crop in the document
RARE_MAX = 4  # a word used at most this often in the document is a specific term
MIN_TERM_CHARS = 8  # ... and at least this long (product or disease names, not 'against')


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z][a-z-]{5,}", text.lower())


def keep_crop_consistent_lines(output: str, source: str) -> tuple[str, int]:
    """Drop dose lines that attach a specific product or disease to a crop the document never
    mentions near it (e.g. a cowpea fungicide presented as advice for rice). Only lines with a
    number are checked; specific terms are rare, long words (8+ letters) of the document."""
    low = source.lower()
    counts: dict[str, int] = {}
    for w in _words(low):
        counts[w] = counts.get(w, 0) + 1
    crop_terms = {t for terms in CROP_WORDS.values() for t in terms}
    kept, dropped = [], 0
    for line in output.splitlines():
        line_low = line.lower()
        if not re.search(r"\d", line_low):
            kept.append(line)
            continue
        crops = [t for t in crop_terms if re.search(r"\b" + re.escape(t) + r"\b", line_low)]
        groups = {tuple(CROP_WORDS[k]) for k in CROP_WORDS for t in crops if t in CROP_WORDS[k]}
        rare = [w for w in set(_words(line_low)) if len(w) >= MIN_TERM_CHARS
                and 0 < counts.get(w, 0) <= RARE_MAX and w not in crop_terms]
        if not groups or not rare:
            kept.append(line)
            continue
        ok = True
        for word in rare:  # every specific term must sit near one of the line's crops
            near = False
            for m in re.finditer(re.escape(word), low):
                window = low[max(0, m.start() - NEAR_CHARS): m.end() + NEAR_CHARS]
                if any(re.search(r"\b" + re.escape(t) + r"\b", window)
                       for g in groups for t in g):
                    near = True
                    break
            ok = ok and near
        if ok:
            kept.append(line)
        else:
            dropped += 1
    return "\n".join(kept).strip(), dropped


def split_parts(text: str, size: int = PART_CHARS) -> list[str]:
    """Split on paragraph breaks into parts of at most ``size`` characters."""
    pieces: list[str] = []
    for para in re.split(r"\n\s*\n", text):  # a paragraph longer than size is cut in pieces
        pieces += [para[i:i + size] for i in range(0, len(para), size)] or [""]
    parts, current = [], ""
    for piece in pieces:
        if len(current) + len(piece) > size and current:
            parts.append(current)
            current = ""
        current += piece + "\n\n"
    if current.strip():
        parts.append(current)
    return parts


class DocumentAnalyzer:
    def __init__(self, llm: Any, translator: Any, parser: Any = None,
                 extractor: Any = None) -> None:
        self._llm, self._translator = llm, translator
        self._parser, self._extractor = parser, extractor

    async def _parse(self, data: bytes, filename: str) -> tuple[str, int]:
        if self._parser is None:
            from app.knowledge.parsers.selector import ParserSelector  # noqa: PLC0415
            self._parser = ParserSelector()
        parsed, _ = await self._parser.parse(data, filename)
        return parsed.full_text, parsed.total_pages

    def _extract(self, text: str) -> dict[str, Any]:
        if self._extractor is None:
            from app.govconnect.extraction import get_extractor  # noqa: PLC0415
            self._extractor = get_extractor()
        return self._extractor.extract(text).to_dict()

    async def analyze(self, data: bytes, filename: str, audience: Audience = "officer",
                      language: str = "en",
                      context: FarmerContext | None = None) -> DocumentAnalysis:
        t: dict[str, float] = {}
        start = perf_counter()
        full_text, pages = await self._parse(data, filename)
        t["parse"] = (perf_counter() - start) * 1000
        all_parts = split_parts(full_text) if full_text.strip() else []
        parts = select_parts(all_parts, context.terms() if context else [])
        text = "".join(parts)
        result = DocumentAnalysis(audience=audience, language=language, text="", text_en="",
                                  pages=pages, chars_read=len(text),
                                  parts_read=len(parts), parts_total=len(all_parts),
                                  truncated=len(parts) < len(all_parts),
                                  model=getattr(self._llm, "model_name", None))
        if not text.strip():
            result.text = result.text_en = "No readable text was found in this document."
            return result

        mark = perf_counter()
        notes = []
        for part in parts:
            reply = await self._llm.generate(f"Text:\n{part}\n\nKey facts:", PART_SYSTEM,
                                             temperature=0.1, max_tokens=400)
            notes.append(reply.content.strip())
        system, fmt = ((OFFICER_SYSTEM, OFFICER_FORMAT) if audience == "officer"
                       else (FARMER_SYSTEM, FARMER_FORMAT))
        focus = context.instruction() if context else ""
        reply = await self._llm.generate("Notes from the document:\n" + "\n".join(notes)
                                         + "\n\n" + focus + fmt, system, temperature=0.1,
                                         max_tokens=500)
        t["summarise"] = (perf_counter() - mark) * 1000
        checked, dropped_numbers = keep_supported_lines(reply.content.strip(), text)
        result.text_en, dropped_crops = keep_crop_consistent_lines(checked, text)
        result.dropped_lines = dropped_numbers + dropped_crops

        if audience == "officer":
            result.extracted = self._extract(text)
        if language != "en":
            mark = perf_counter()
            out = await self._translator.translate(result.text_en, "en", language,
                                                   personal_data=True)
            t["translate"] = (perf_counter() - mark) * 1000
            result.translation_failed = not out.deliverable
            result.text = out.text if out.deliverable else result.text_en
        else:
            result.text = result.text_en
        t["total"] = (perf_counter() - start) * 1000
        result.timings_ms = {k: round(v, 1) for k, v in t.items()}
        return result
