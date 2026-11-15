"""Deterministic multilingual NLU and NLU-based planner routing."""

import pytest
from app.agents.planner.planner import PlanningEngine
from app.config.settings import get_settings
from app.nlu import service
from app.nlu.service import parse_sync
from app.nlu.types import Intent


@pytest.mark.parametrize(
    ("text", "intent", "language", "crop"),
    [
        ("What is the yield forecast for paddy in Khammam?", Intent.YIELD, "en", "paddy"),
        ("నా వరి పైరుకు అగ్గి తెగులు వచ్చింది, ఏమి చేయాలి?", Intent.DISEASE, "te", "paddy"),
        ("धान की फसल में भूरा धब्बा रोग का इलाज क्या है?", Intent.DISEASE, "hi", "paddy"),
        ("mirchi lo thrips ekkuva unnayi em cheyali", Intent.DISEASE, "te", "chilli"),
        ("mere gehun me keede lag gaye kya karein", Intent.DISEASE, "hi", "wheat"),
        ("Will it rain tomorrow in Guntur district?", Intent.WEATHER, "en", None),
        ("పత్తి ధర వరంగల్ మార్కెట్ లో ఎంత?", Intent.MARKET, "te", "cotton"),
        ("Am I eligible for PM-KISAN?", Intent.SCHEME, "en", None),
        ("What did the department say about spraying this week?", Intent.GOVT_BULLETIN, "en", None),
        ("pathi pantaki digubadi entha vastundi", Intent.YIELD, "te", "cotton"),
        ("who won the cricket match", Intent.OUT_OF_SCOPE, "en", None),
        ("नमस्ते", Intent.SMALLTALK, "hi", None),
    ],
)
def test_intent_language_crop(text, intent, language, crop) -> None:
    r = parse_sync(text)
    assert r.intent is intent, r
    assert r.language == language
    assert r.entities.crop == crop


def test_code_switching_flags() -> None:
    mixed = parse_sync("నా వరి crop కి yellow spots వస్తున్నాయి")
    assert mixed.language == "te" and mixed.is_code_switched and not mixed.romanized
    roman = parse_sync("mirchi lo thrips ekkuva unnayi em cheyali")
    assert roman.romanized and roman.is_code_switched
    assert not parse_sync("My cotton has pink bollworm").is_code_switched


def test_yield_beats_weather_forecast() -> None:
    r = parse_sync("yield forecast for maize this season")
    assert r.intent is Intent.YIELD
    assert Intent.WEATHER not in r.secondary_intents


def test_district_entities_and_collisions() -> None:
    assert parse_sync("rain in Khammam").entities.district_lgd_code == 509
    # 'Mandi' is a Himachal district AND the word for market: only a district when marked.
    assert parse_sync("mandi price of cotton").entities.district_lgd_code is None
    assert parse_sync("weather in Mandi district").entities.district_name == "Mandi"
    # Duplicate names stay ambiguous rather than guessed.
    amb = parse_sync("rain in Bilaspur")
    assert amb.entities.district_lgd_code is None
    assert set(amb.entities.district_candidates) == {15, 375}


def test_ambiguous_crop_is_surfaced() -> None:
    e = parse_sync("gobhi me keede").entities
    assert e.crop is None and e.crop_status == "ambiguous"
    assert set(e.crop_candidates) == {"cabbage", "cauliflower"}


def test_entities_season_time_scheme_symptoms() -> None:
    e = parse_sync("rabi wheat yellow leaves, PMFBY claim tomorrow").entities
    assert e.season == "rabi" and e.time_expression == "tomorrow" and e.scheme == "pmfby"
    assert "yellowing" in e.symptoms


def test_planner_routes_telugu_weather_and_yield() -> None:
    planner = PlanningEngine()
    te_weather = [s.agent for s in planner.build_plan("రేపు ఖమ్మంలో వర్షం పడుతుందా?").steps]
    assert "weather_intelligence_agent" in te_weather
    yield_plan = [s.agent for s in planner.build_plan("yield forecast for paddy").steps]
    assert "weather_intelligence_agent" not in yield_plan
    assert "crop_advisory_agent" in yield_plan


def test_planner_no_officer_agent_for_farmer_naming_district() -> None:
    agents = [s.agent for s in PlanningEngine().build_plan("My paddy in Khammam district").steps]
    assert "officer_assistance_agent" not in agents


def test_planner_passes_entities_to_steps() -> None:
    plan = PlanningEngine().build_plan("cotton pink bollworm in Warangal")
    retrieval = next(s for s in plan.steps if s.agent == "knowledge_retrieval_agent")
    assert retrieval.parameters["crop"] == "Cotton"
    assert retrieval.parameters["crop_canonical"] == "cotton"
    assert retrieval.parameters["intent"] == "disease"


async def test_service_skips_off_device_for_personal_data(monkeypatch) -> None:
    s = get_settings()
    monkeypatch.setattr(s, "NLU_PROVIDER", "gemini-nlu")
    monkeypatch.setattr(s, "NLU_FALLBACK_PROVIDER", "rule-based-nlu")
    monkeypatch.setattr(s, "ALLOW_OFF_DEVICE_PROVIDERS", False)
    r = await service.parse("paddy blast", personal_data=True)
    assert r.provider == "rule-based-nlu"


def test_nlu_endpoint_requires_auth(client) -> None:
    assert client.post("/api/v1/nlu/parse", json={"text": "hello"}).status_code in {401, 403}
