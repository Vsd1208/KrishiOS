"""Photo questions: the crop is confirmed by the farmer when the model is unsure, findings are
hints (never a diagnosis), and the answer carries vision / yield / bulletin cards."""

from types import SimpleNamespace
from uuid import uuid4

from app.conversation import api
from app.conversation.answer import AnswerContext, AssembledAnswer
from app.conversation.manager import (
    ConversationManager,
    FarmerProfile,
    TurnInput,
    vision_to_dict,
)
from app.surveillance import service
from app.vision.providers.mock_provider import MockVisionProvider


class Runner:
    def __init__(self) -> None:
        self.calls: list[AnswerContext] = []

    async def run(self, ctx: AnswerContext) -> AssembledAnswer:
        self.calls.append(ctx)
        return AssembledAnswer(text_en="Remove infected leaves; spray as per label.",
                               citations=[{"title": "ICAR"}], agents=["crop_advisory"],
                               grounded=True, confidence=0.8)


def vision(crop=None, supported=False, cands=(("tomato", 0.4), ("potato", 0.3)),
           conds=(("early blight", 0.7),)):
    return {"crop_detected": crop, "crop_supported": supported,
            "crop_candidates": [list(c) for c in cands],
            "candidate_conditions": [{"name": n, "confidence": c} for n, c in conds],
            "model_name": "krishios-vision-test", "model_version": "t1"}


def bot(reclassified=None):
    runner, calls = Runner(), {"reclassify": [], "bulletins": []}

    async def reclassify(path, crop):
        calls["reclassify"].append((path, crop))
        return reclassified or vision(crop, True, conds=(("late blight", 0.6),))

    async def yield_lookup(lgd, crop, season):
        return {"crop_canonical": crop, "abstained": True}

    async def bulletins(lgd, crop, language):
        calls["bulletins"].append((lgd, crop, language))
        return [{"title": "Heavy rain warning", "severity": "HIGH"}]

    m = ConversationManager(runner=runner, photo_reclassify=reclassify,
                            yield_lookup=yield_lookup, bulletin_lookup=bulletins)
    return m, runner, calls


def photo_turn(v, text="What is wrong with my crop in this photo?", **kw):
    return TurnInput(user_uuid="u1", text=text, language="en",
                     photo={"path": "leaf.jpg", "vision": v}, **kw)


PROFILE = FarmerProfile(district_lgd_code=509, crops=["paddy"])


async def test_confident_photo_fills_the_crop_and_adds_cards() -> None:
    m, runner, calls = bot()
    r = await m.handle(photo_turn(vision("tomato", True), profile=PROFILE))
    assert r.status == "answered" and r.slots["crop"] == "tomato"
    goal = runner.calls[0].goal_en
    assert "not a diagnosis" in goal and "early blight" in goal
    assert r.vision["crop"] == "tomato" and r.vision["official"] is False
    assert not r.vision["crop_confirmed_by_farmer"] and calls["reclassify"] == []
    assert r.bulletins[0]["title"] == "Heavy rain warning" and r.yield_forecast["official"] is False


async def test_unsure_photo_asks_with_chips_then_rereads_for_the_confirmed_crop() -> None:
    m, runner, calls = bot()
    first = await m.handle(photo_turn(vision(None, False), profile=PROFILE))
    assert first.status == "clarification" and first.clarification["slot"] == "crop"
    values = [c["value"] for c in first.clarification["choices"]]
    assert values[:2] == ["tomato", "potato"] and "paddy" in values  # photo first, then mine
    second = await m.handle(TurnInput(user_uuid="u1", text="", language="en",
                                      conversation_id=first.conversation_id,
                                      choice={"slot": "crop", "value": "potato"},
                                      profile=PROFILE))
    assert second.status == "answered" and second.slots["crop"] == "potato"
    assert calls["reclassify"] == [("leaf.jpg", "potato")]
    assert second.vision["crop_confirmed_by_farmer"] and "late blight" in runner.calls[0].goal_en


async def test_mock_findings_never_reach_the_dialogue(tmp_path) -> None:
    r = await MockVisionProvider().analyze(tmp_path / "leaf.jpg", {})
    assert r.candidate_conditions and vision_to_dict(r)["candidate_conditions"] == []


async def test_a_failed_surveillance_write_does_not_lose_the_answer(monkeypatch) -> None:
    class Nested:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    class Session:
        committed = False

        def begin_nested(self):
            return Nested()

        async def commit(self):
            self.committed = True

    async def broken(*args, **kwargs):
        raise RuntimeError("table missing")

    monkeypatch.setattr(service, "record", broken)
    session = Session()
    result = SimpleNamespace(status="answered", slots={"district_lgd_code": 509, "crop": "paddy"},
                             vision={"candidate_conditions": [{"name": "blast",
                                                               "confidence": 0.8}]})
    await api._record_diagnosis(session, SimpleNamespace(user_uuid=uuid4()), result)
    assert not session.committed


async def test_farmer_words_beat_the_photo() -> None:
    m, _, calls = bot()
    r = await m.handle(photo_turn(vision("tomato", True), text="my paddy leaves have spots",
                                  profile=PROFILE))
    assert r.slots["crop"] == "paddy" and calls["reclassify"] == [("leaf.jpg", "paddy")]
