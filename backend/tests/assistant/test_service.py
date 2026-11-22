"""Phase 10c assistant: answers only from cited passages, abstains otherwise."""

from dataclasses import dataclass

from app.agents.providers.llm import LLMResponse
from app.assistant.service import (
    NO_SOURCE,
    NOT_IN_SOURCES,
    AssistantService,
    Passage,
    build_prompt,
    cited_numbers,
)

PASSAGES = [Passage("Apply urea in two equal splits at 3 and 6 weeks after transplanting.",
                    "Package of Practices for Kharif Crops", 30, "https://example/pp.pdf", 0.85),
            Passage("Sow the nursery from 25 May to 20 June.", "Package of Practices", 12,
                    None, 0.80)]


class FakeLLM:
    model_name = "fake"

    def __init__(self, reply: str) -> None:
        self.reply, self.prompts = reply, []

    async def generate(self, prompt, system_instruction=None, temperature=0.2, max_tokens=1000):
        self.prompts.append(prompt)
        return LLMResponse(content=self.reply, model_name="fake")


@dataclass
class Out:
    text: str
    deliverable: bool = True


class FakeTranslator:
    def __init__(self, deliverable: bool = True) -> None:
        self.calls, self.deliverable = [], deliverable

    async def translate(self, text, source_language, target_language, **kw):
        self.calls.append((source_language, target_language, kw.get("personal_data")))
        ok = self.deliverable or target_language == "en"
        return Out(f"<{target_language}>{text}", ok)


def searcher(passages):
    async def search(query_en, top_k):
        search.queries.append(query_en)
        return passages
    search.queries = []
    return search


async def test_answer_with_citations_is_translated_back() -> None:
    llm, tr, se = FakeLLM("Apply urea at 3 and 6 weeks [1]."), FakeTranslator(), searcher(PASSAGES)
    out = await AssistantService(llm, se, tr).ask("बासमती में यूरिया कब?", "hi")
    assert out.answered and out.citations[0]["page"] == 30
    assert se.queries == ["<en>बासमती में यूरिया कब?"]  # searched in English
    assert out.answer == "<hi>Apply urea at 3 and 6 weeks [1]."
    assert tr.calls == [("hi", "en", True), ("en", "hi", True)]  # farmer text stays local
    assert "[1] (Package of Practices for Kharif Crops, page 30)" in llm.prompts[0]


async def test_not_in_sources_abstains() -> None:
    out = await AssistantService(FakeLLM(NOT_IN_SOURCES), searcher(PASSAGES),
                                 FakeTranslator()).ask("Dragon fruit spacing?", "en")
    assert not out.answered and out.answer == NO_SOURCE["en"] and out.citations == []


async def test_uncited_answer_is_not_shown() -> None:
    out = await AssistantService(FakeLLM("Use 50 kg urea per acre."), searcher(PASSAGES),
                                 FakeTranslator()).ask("How much urea?", "te")
    assert not out.answered and out.answer == NO_SOURCE["te"]


async def test_no_passages_skips_the_model() -> None:
    llm = FakeLLM("anything [1]")
    out = await AssistantService(llm, searcher([]), FakeTranslator()).ask("q", "en")
    assert not out.answered and llm.prompts == []


async def test_failed_translation_returns_english_with_flag() -> None:
    out = await AssistantService(FakeLLM("Apply 25 kg zinc sulphate per acre [1]."),
                                 searcher(PASSAGES), FakeTranslator(deliverable=False)
                                 ).ask("q", "te")
    assert out.answered and out.translation_failed
    assert out.answer == "Apply 25 kg zinc sulphate per acre [1]."


def test_cited_numbers_ignores_out_of_range_and_repeats() -> None:
    assert cited_numbers("a [2]. b [1, 2]. c [9].", 2) == [2, 1]
    assert "Question: q" in build_prompt("q", PASSAGES)
