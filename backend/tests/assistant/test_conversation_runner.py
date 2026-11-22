"""The grounded assistant as the conversation's answer runner (CONVERSATION_ANSWER_RUNNER)."""

from app.assistant.service import AssistantAnswer
from app.config.settings import get_settings
from app.conversation.answer import (
    AnswerContext,
    AssistantAnswerRunner,
    RuntimeAnswerRunner,
    build_answer_runner,
)


class _Fake:
    def __init__(self, answered: bool) -> None:
        self.answered, self.calls = answered, []

    async def ask(self, question: str, language: str) -> AssistantAnswer:
        self.calls.append((question, language))
        if not self.answered:
            return AssistantAnswer(question=question, language=language, answered=False,
                                   answer="no source", answer_en="no source")
        return AssistantAnswer(question=question, language=language, answered=True,
                               answer="Sow 1 April to 15 May [1].",
                               answer_en="Sow 1 April to 15 May [1].",
                               citations=[{"n": 1, "title": "PAU Kharif", "page": 54,
                                           "source_url": "u", "similarity": 0.86}])


async def test_cited_answer_becomes_grounded_text_without_markers() -> None:
    fake = _Fake(answered=True)
    out = await AssistantAnswerRunner(fake).run(AnswerContext(goal_en="When to sow Bt cotton?",
                                                              session_id="s"))
    assert fake.calls == [("When to sow Bt cotton?", "en")]  # manager already translated
    assert out.text_en == "Sow 1 April to 15 May." and out.grounded
    assert out.citations == [{"title": "PAU Kharif", "page": 54, "source": "u",
                              "relevance": 0.86}]
    assert out.confidence == 0.86 and not out.requires_review


async def test_decline_returns_empty_text_for_review() -> None:
    out = await AssistantAnswerRunner(_Fake(answered=False)).run(
        AnswerContext(goal_en="Dragon fruit spacing?", session_id="s"))
    assert out.text_en == "" and not out.grounded
    assert out.requires_review and out.review_reason == "no_source"


def test_setting_selects_the_runner(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "CONVERSATION_ANSWER_RUNNER", "assistant")
    assert isinstance(build_answer_runner(), AssistantAnswerRunner)
    monkeypatch.setattr(settings, "CONVERSATION_ANSWER_RUNNER", "agents")
    assert isinstance(build_answer_runner(), RuntimeAnswerRunner)
