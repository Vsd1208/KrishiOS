"""Multi-turn dialogue behaviour (agent runtime replaced by a fake answer runner)."""

from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from app.conversation.answer import AnswerContext, AssembledAnswer, assemble
from app.conversation.manager import ConversationManager, FarmerProfile, TurnInput
from app.translation.service import TranslationStatus

USER = "user-1"
CITE = {"title": "ICAR Rice Package of Practices", "source": "ICAR"}


class FakeRunner:
    def __init__(self, text: str = "Spray Tricyclazole 75% WP at 0.6 g/L.", **kw) -> None:
        self.calls: list[AnswerContext] = []
        self.answer = AssembledAnswer(text_en=text, citations=[CITE], agents=["crop_advisory"],
                                      grounded=True, confidence=0.8, **kw)

    async def run(self, ctx: AnswerContext) -> AssembledAnswer:
        self.calls.append(ctx)
        return self.answer


@dataclass
class FakeOutcome:
    text: str
    status: TranslationStatus
    provider: str = "fake"


class BlockingTranslator:
    async def translate(self, text, src, tgt, **kw):
        return FakeOutcome(text, TranslationStatus.BLOCKED)


@pytest.fixture
def runner() -> FakeRunner:
    return FakeRunner()


@pytest.fixture
def bot(runner) -> ConversationManager:
    return ConversationManager(runner=runner)


async def turn(bot, text, lang="en", cid=None, **kw):
    return await bot.handle(TurnInput(user_uuid=USER, text=text, language=lang,
                                      conversation_id=cid, **kw))


async def test_telugu_question_is_answered_in_telugu(bot, runner) -> None:
    r = await turn(bot, "నా వరి పైరుకు అగ్గి తెగులు వచ్చింది, ఏమి చేయాలి?", lang="te")
    assert r.status == "answered" and r.intent == "disease" and r.language == "te"
    assert r.slots["crop"] == "paddy"
    assert runner.calls[0].crop_name_en == "Paddy"
    assert r.reply_text.startswith("[MOCK en->te]")  # mock translation is labelled, never hidden
    assert r.citations == [CITE]
    assert r.providers["translation_out"]["provider"] == "mock-translation"


async def test_ambiguous_crop_asks_then_resumes_with_choice(bot, runner) -> None:
    r1 = await turn(bot, "gobhi me keede lag gaye", lang="hi")
    assert r1.status == "clarification" and r1.clarification["slot"] == "crop"
    labels = {c["value"]: c["label"] for c in r1.clarification["choices"]}
    assert labels == {"cabbage": "पत्तागोभी", "cauliflower": "फूलगोभी"}
    assert runner.calls == []  # nothing answered before the crop is known

    r2 = await turn(bot, "", lang="hi", cid=r1.conversation_id,
                    choice={"slot": "crop", "value": "cauliflower"})
    assert r2.status == "answered" and r2.slots["crop"] == "cauliflower"
    assert r2.resumed_question == "gobhi me keede lag gaye"
    assert runner.calls[0].crop_name_en == "Cauliflower"


async def test_clarification_answered_by_typing_the_label(bot) -> None:
    r1 = await turn(bot, "gobhi me keede", lang="hi")
    r2 = await turn(bot, "फूलगोभी", lang="hi", cid=r1.conversation_id)
    assert r2.status == "answered" and r2.slots["crop"] == "cauliflower"


async def test_missing_crop_offers_profile_crops(bot) -> None:
    profile = FarmerProfile(crops=["paddy", "cotton"])
    r1 = await turn(bot, "my leaves have brown spots", profile=profile)
    assert r1.clarification["slot"] == "crop"
    assert {c["value"] for c in r1.clarification["choices"]} == {"paddy", "cotton"}
    r2 = await turn(bot, "cotton", cid=r1.conversation_id, profile=profile)
    assert r2.status == "answered" and r2.slots["crop"] == "cotton"


async def test_weather_uses_profile_district_without_asking(bot, runner) -> None:
    r = await turn(bot, "will it rain tomorrow?", profile=FarmerProfile(district_lgd_code=509))
    assert r.status == "answered" and r.slots["district_name"] == "Khammam"
    assert runner.calls[0].district == "Khammam" and runner.calls[0].state == "Telangana"


async def test_weather_without_district_asks(bot) -> None:
    r = await turn(bot, "will it rain tomorrow?", lang="te")
    assert r.clarification == {"slot": "district", "question": "మీ పొలం ఏ జిల్లాలో ఉంది?",
                               "choices": []}
    r2 = await turn(bot, "Khammam", lang="te", cid=r.conversation_id)
    assert r2.status == "answered" and r2.slots["district_lgd_code"] == 509


async def test_duplicate_district_name_offers_choices(bot) -> None:
    r = await turn(bot, "rain in Bilaspur tomorrow")
    assert r.clarification["slot"] == "district"
    assert {c["value"] for c in r.clarification["choices"]} == {15, 375}


async def test_crop_carries_over_to_follow_up(bot, runner) -> None:
    r1 = await turn(bot, "paddy blast disease")
    r2 = await turn(bot, "how much fertilizer should I apply?", cid=r1.conversation_id)
    assert r2.status == "answered" and r2.slots["crop"] == "paddy"
    assert runner.calls[-1].crop_name_en == "Paddy"


async def test_smalltalk_and_out_of_scope(bot, runner) -> None:
    hello = await turn(bot, "నమస్కారం", lang="te")
    assert hello.status == "smalltalk" and hello.reply_text.startswith("నమస్కారం!")
    other = await turn(bot, "who won the cricket match", lang="hi")
    assert other.status == "refused" and "खेती" in other.reply_text
    assert runner.calls == []


async def test_blocked_translation_shows_english_and_escalates(runner) -> None:
    bot = ConversationManager(runner=runner, translator=BlockingTranslator())
    r = await turn(bot, "paddy blast disease", lang="te")
    assert r.translation_status == "blocked"
    assert runner.answer.text_en in r.reply_text  # English answer, never the unverified text
    assert r.reply_text.startswith("ఈ సమాధానానికి ధృవీకరించిన అనువాదం")
    assert r.requires_review and r.review_reason == "translation_unverified"


async def test_empty_answer_is_escalated() -> None:
    bot = ConversationManager(runner=FakeRunner(text=""))
    r = await turn(bot, "paddy blast disease", lang="hi")
    assert r.requires_review and "कृषि अधिकारी" in r.reply_text


async def test_other_user_cannot_resume_conversation(bot) -> None:
    r1 = await turn(bot, "gobhi me keede", lang="hi")
    other = await bot.handle(TurnInput(user_uuid="intruder", text="cauliflower", language="hi",
                                       conversation_id=r1.conversation_id))
    assert other.conversation_id != r1.conversation_id
    assert other.resumed_question is None


async def test_tts_optional_and_failure_tolerant(runner) -> None:
    class GoodTTS:
        async def synthesize(self, text, language):
            return SimpleNamespace(audio_uuid="a1", model_name="mock-tts", model_version="0")

    class BadTTS:
        async def synthesize(self, text, language):
            raise RuntimeError("model missing")

    ok = await ConversationManager(runner=runner, tts=GoodTTS()).handle(
        TurnInput(user_uuid=USER, text="paddy blast", language="en", speak=True))
    assert ok.audio_uuid == "a1"
    bad = await ConversationManager(runner=runner, tts=BadTTS()).handle(
        TurnInput(user_uuid=USER, text="paddy blast", language="en", speak=True))
    assert bad.audio_uuid is None and bad.status == "answered"


def test_assemble_prefers_advisory_text_and_merges_citations() -> None:
    results = [
        SimpleNamespace(agent_name="knowledge_retrieval_agent", output={"hits": []},
                        citations=[CITE], confidence_score=0.7, grounded=True),
        SimpleNamespace(agent_name="crop_advisory_agent", output={"recommendation": "Do X."},
                        citations=[CITE], confidence_score=0.8, grounded=True),
        SimpleNamespace(agent_name="response_validation_agent", output={}, citations=[],
                        confidence_score=0.1, grounded=False),
    ]
    a = assemble(results)
    assert a.text_en == "Do X." and a.citations == [CITE] and not a.requires_review


def test_assemble_flags_ungrounded() -> None:
    a = assemble([SimpleNamespace(agent_name="crop_advisory_agent",
                                  output={"recommendation": "Guess."}, citations=[],
                                  confidence_score=0.9, grounded=False)])
    assert a.requires_review and a.review_reason == "not_grounded"


async def test_unfilled_reply_re_asks_and_keeps_the_question(bot, runner) -> None:
    r1 = await turn(bot, "Will it rain tomorrow?")
    assert r1.clarification["slot"] == "district"
    r2 = await turn(bot, "the one near my village", cid=r1.conversation_id)
    assert r2.status == "clarification" and r2.clarification["slot"] == "district"
    assert runner.calls == []
    r3 = await turn(bot, "Khammam", cid=r1.conversation_id)
    assert r3.status == "answered" and r3.intent == "weather"
    assert r3.slots["district_lgd_code"] == 509
    assert r3.resumed_question == "Will it rain tomorrow?"


async def test_ambiguous_district_reply_offers_choices_then_resumes(bot, runner) -> None:
    r1 = await turn(bot, "What will be the wheat yield this year?")
    assert r1.clarification["slot"] == "district"
    r2 = await turn(bot, "Bilaspur", cid=r1.conversation_id)
    assert r2.status == "clarification" and r2.clarification["slot"] == "district"
    values = {c["value"] for c in r2.clarification["choices"]}
    assert 375 in values and len(values) > 1
    r3 = await turn(bot, "", cid=r1.conversation_id, choice={"slot": "district", "value": 375})
    assert r3.status == "answered" and r3.intent == "yield"
    assert r3.slots["crop"] == "wheat" and r3.slots["district_lgd_code"] == 375
