"""Phase 10c: analyse an uploaded document for an officer (brief) or a farmer (plain summary).

- The file is parsed in memory (PDF, DOCX, TXT, image OCR) and never stored: a farmer's upload
  is personal data and is processed only on this machine (local parsers, on-device LLM, local
  translation).
- Officer brief: the deterministic GovConnect extractor (dates, places, crops, hazards, actions,
  each with its source span) plus an LLM summary in a fixed layout.
- Farmer summary: three plain sentences and "what to do", translated to the farmer's language.
- Long documents are summarised part by part, then combined; text beyond ``MAX_CHARS`` is not
  read, and the answer says so.
- Safety check: an output line with a number that does not occur in the document is dropped and
  counted (``dropped_lines``), so a dose or date cannot be invented.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Literal

PART_CHARS = 6000
MAX_CHARS = 30000  # five parts; longer documents are cut and the result says so
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
    truncated: bool = False
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


def split_parts(text: str, size: int = PART_CHARS) -> list[str]:
    """Split on paragraph breaks into parts of at most ``size`` characters."""
    parts, current = [], ""
    for para in re.split(r"\n\s*\n", text):
        if len(current) + len(para) > size and current:
            parts.append(current)
            current = ""
        current += para[:size] + "\n\n"
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
                      language: str = "en") -> DocumentAnalysis:
        t: dict[str, float] = {}
        start = perf_counter()
        full_text, pages = await self._parse(data, filename)
        t["parse"] = (perf_counter() - start) * 1000
        text = full_text[:MAX_CHARS]
        result = DocumentAnalysis(audience=audience, language=language, text="", text_en="",
                                  pages=pages, chars_read=len(text),
                                  truncated=len(full_text) > MAX_CHARS,
                                  model=getattr(self._llm, "model_name", None))
        if not text.strip():
            result.text = result.text_en = "No readable text was found in this document."
            return result

        mark = perf_counter()
        notes = []
        for part in split_parts(text):
            reply = await self._llm.generate(f"Text:\n{part}\n\nKey facts:", PART_SYSTEM,
                                             temperature=0.1, max_tokens=400)
            notes.append(reply.content.strip())
        system, fmt = ((OFFICER_SYSTEM, OFFICER_FORMAT) if audience == "officer"
                       else (FARMER_SYSTEM, FARMER_FORMAT))
        reply = await self._llm.generate("Notes from the document:\n" + "\n".join(notes)
                                         + "\n\n" + fmt, system, temperature=0.1,
                                         max_tokens=500)
        t["summarise"] = (perf_counter() - mark) * 1000
        result.text_en, result.dropped_lines = keep_supported_lines(reply.content.strip(), text)

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
