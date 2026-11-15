"""Yield questions are answered from the forecast provider, never from the LLM runtime."""

from app.conversation.manager import ConversationManager, TurnInput

FORECAST = {
    "lgd_district_code": 509, "crop_canonical": "paddy", "season": "Rabi", "crop_year": 2026,
    "crop_tier": "A", "forecast_lead": 30, "unit": "Tonnes/Hectare", "model_name": "b3",
    "model_version": "v1", "generated_at": "2026-11-15T00:00:00+00:00",
    "predicted_yield": 2.8, "interval_low": 2.3, "interval_high": 3.3, "normal_yield": 3.5,
    "available_modalities": ["weather", "yield_history"], "missing_modalities": [],
    "in_distribution": True, "requires_human_review": False, "abstained": False,
    "abstain_reason": None, "district_id": None, "change_vs_normal": 2.8 / 3.5 - 1,
}


class NoRunner:
    async def run(self, ctx):  # the agent runtime must not be used for yield questions
        raise AssertionError("runtime called")


def bot(result):
    calls = []

    async def lookup(lgd, crop, season):
        calls.append((lgd, crop, season))
        return result

    return ConversationManager(runner=NoRunner(), yield_lookup=lookup), calls


async def ask(m, text, lang="en"):
    return await m.handle(TurnInput(user_uuid="u1", text=text, language=lang))


async def test_yield_answer_has_numbers_card_and_disclaimer() -> None:
    m, calls = bot(FORECAST)
    r = await ask(m, "What is the yield forecast for paddy in Khammam?")
    assert r.status == "answered" and r.intent == "yield"
    assert calls == [(509, "paddy", None)]
    assert "2.80 t/ha" in r.reply_text and "2.30-3.30" in r.reply_text
    assert "20% below normal" in r.reply_text and "not an official" in r.reply_text
    assert r.yield_forecast["official"] is False and not r.requires_review


async def test_tier_b_forecast_is_flagged_for_review() -> None:
    m, _ = bot({**FORECAST, "crop_tier": "B", "requires_human_review": True})
    r = await ask(m, "What is the yield forecast for paddy in Khammam?")
    assert r.requires_review and r.review_reason == "yield_uncertain"
    assert "officer will review" in r.reply_text


async def test_abstention_gives_no_number() -> None:
    m, _ = bot({**FORECAST, "crop_tier": "C", "abstained": True, "predicted_yield": None,
                "interval_low": None, "interval_high": None, "normal_yield": None,
                "abstain_reason": "insufficient data", "change_vs_normal": None})
    r = await ask(m, "What is the yield forecast for paddy in Khammam?")
    assert "not enough data" in r.reply_text and not any(ch.isdigit() for ch in r.reply_text)


async def test_missing_forecast_is_said_plainly() -> None:
    m, _ = bot(None)
    r = await ask(m, "What is the yield forecast for paddy in Khammam?")
    assert "no yield forecast" in r.reply_text and r.yield_forecast is None


async def test_telugu_yield_answer_uses_template_not_translation() -> None:
    m, _ = bot(FORECAST)
    first = await ask(m, "వరి దిగుబడి అంచనా ఎంత?", lang="te")
    assert first.status == "clarification" and first.clarification["slot"] == "district"
    # District names resolve in Latin script only (Telugu-script names: gap, report 08).
    r = await m.handle(TurnInput(user_uuid="u1", text="Khammam", language="te",
                                 conversation_id=first.conversation_id))
    assert r.intent == "yield" and "2.80 t/ha" in r.reply_text
    assert "[MOCK" not in r.reply_text  # fixed localized template, not machine translation
