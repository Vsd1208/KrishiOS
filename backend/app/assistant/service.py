"""Phase 10c: KrishiOS assistant: answers questions only from the vetted guides, or says it can't.

Flow for a question in English, Hindi or Telugu:

1. Hindi/Telugu questions are translated to English (searching in English found the right guide
   page far more often: dev hit@5 te 0.3 -> 0.8, ML run 894e4efc957b).
2. The guides are searched; the best passages are numbered [1]..[n] with title and page.
3. The on-device LLM answers in English **only from those passages**, citing them, or replies
   ``NOT_IN_SOURCES``. An answer with no valid citation is treated the same way: the farmer is
   told there is no verified source, never given an unsupported answer.
4. The answer is translated back. If the translation fails its checks (numbers, units, protected
   terms), the English answer is returned with ``translation_failed`` set, so a dose is never
   shown garbled.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

NOT_IN_SOURCES = "NOT_IN_SOURCES"
SUPPORTED = ("en", "hi", "te")
TOP_K = 5
MAX_PASSAGE_CHARS = 900

SYSTEM = (
    "You are KrishiOS, an agricultural extension assistant for Indian farmers. "
    "Answer ONLY from the numbered passages you are given. Every sentence must end with the "
    "passage number(s) it comes from, like [2]. Keep doses, units, timings and product names "
    "exactly as written in the passage. If the passages do not answer the question, reply "
    f"with exactly {NOT_IN_SOURCES} and nothing else. Never use outside knowledge."
)


@dataclass(frozen=True, slots=True)
class Passage:
    text: str
    title: str | None
    page: int | None
    source_url: str | None
    similarity: float


@dataclass(slots=True)
class AssistantAnswer:
    question: str
    language: str
    answered: bool
    answer: str  # in ``language`` (or English when translation_failed)
    answer_en: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    query_en: str = ""
    translation_failed: bool = False
    timings_ms: dict[str, float] = field(default_factory=dict)
    model: str | None = None


class Searcher(Protocol):
    async def __call__(self, query_en: str, top_k: int) -> list[Passage]: ...


class Translator(Protocol):
    async def translate(self, text: str, source_language: str, target_language: str,
                        **kwargs: Any) -> Any: ...


NO_SOURCE = {
    "en": "I could not find this in the verified farming guides I use, so I can't give a reliable "
          "answer. Please ask your agriculture officer or the nearest KVK.",
    "hi": "मुझे यह जानकारी उन सत्यापित खेती मार्गदर्शिकाओं में नहीं मिली जिनका मैं उपयोग करता हूँ, "
          "इसलिए मैं भरोसेमंद उत्तर नहीं दे सकता। कृपया अपने कृषि अधिकारी या नज़दीकी केवीके से पूछें।",
    "te": "నేను ఉపయోగించే ధృవీకరించిన వ్యవసాయ మార్గదర్శకాలలో ఈ సమాచారం దొరకలేదు, కాబట్టి నమ్మదగిన "
          "సమాధానం ఇవ్వలేను. దయచేసి మీ వ్యవసాయ అధికారిని లేదా దగ్గరలోని కేవీకేను అడగండి.",
}


def build_prompt(question_en: str, passages: list[Passage]) -> str:
    blocks = []
    for i, p in enumerate(passages, start=1):
        where = f"{p.title or 'Guide'}, page {p.page}" if p.page else (p.title or "Guide")
        text = " ".join(p.text.split())[:MAX_PASSAGE_CHARS]
        blocks.append(f"[{i}] ({where})\n{text}")
    return ("Passages:\n\n" + "\n\n".join(blocks)
            + f"\n\nQuestion: {question_en}\n\nAnswer in 2-5 short sentences, citing passages.")


_MARKER = re.compile(r"\s*\[\d+(?:\s*,\s*\d+)*\]")


def strip_markers(text: str) -> str:
    """Remove [n] citation markers (sources are listed separately). The translation checks
    treat a marker that comes back as "[ 1 ]" as a leftover placeholder and block the text."""
    return _MARKER.sub("", text).strip()


def cited_numbers(answer: str, n_passages: int) -> list[int]:
    """Passage numbers cited as [k] or [k, m] that exist, in order of first use."""
    seen: list[int] = []
    for group in re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\]", answer):
        for k in (int(x) for x in group.split(",")):
            if 1 <= k <= n_passages and k not in seen:
                seen.append(k)
    return seen


class AssistantService:
    def __init__(self, llm: Any, search: Searcher, translator: Translator) -> None:
        self._llm = llm
        self._search = search
        self._translator = translator

    async def _to(self, text: str, src: str, tgt: str) -> tuple[str, bool]:
        """Translate; returns (text, deliverable). Farmer text is personal data (stays local)."""
        if src == tgt:
            return text, True
        out = await self._translator.translate(text, src, tgt, personal_data=True)
        return out.text, bool(out.deliverable)

    async def ask(self, question: str, language: str = "en") -> AssistantAnswer:
        if language not in SUPPORTED:
            raise ValueError(f"language must be one of {SUPPORTED}")
        t: dict[str, float] = {}
        start = perf_counter()
        query_en, _ = await self._to(question, language, "en")
        t["translate_in"] = (perf_counter() - start) * 1000

        mark = perf_counter()
        passages = await self._search(query_en, TOP_K)
        t["search"] = (perf_counter() - mark) * 1000

        result = AssistantAnswer(question=question, language=language, answered=False,
                                 answer=NO_SOURCE[language], answer_en=NO_SOURCE["en"],
                                 query_en=query_en, model=getattr(self._llm, "model_name", None))
        if passages:
            mark = perf_counter()
            reply = await self._llm.generate(build_prompt(query_en, passages),
                                             system_instruction=SYSTEM, temperature=0.1,
                                             max_tokens=350)
            t["generate"] = (perf_counter() - mark) * 1000
            text = reply.content.strip()
            used = [] if NOT_IN_SOURCES in text else cited_numbers(text, len(passages))
            if used:  # no valid citation -> treated as not found
                result.answered = True
                result.answer_en = text
                result.citations = [
                    {"n": k, "title": passages[k - 1].title, "page": passages[k - 1].page,
                     "source_url": passages[k - 1].source_url}
                    for k in used]
                mark = perf_counter()
                translated, ok = await self._to(strip_markers(text), "en", language)
                t["translate_out"] = (perf_counter() - mark) * 1000
                result.answer = translated if ok else text
                result.translation_failed = not ok
        t["total"] = (perf_counter() - start) * 1000
        result.timings_ms = {k: round(v, 1) for k, v in t.items()}
        return result
