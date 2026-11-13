"""Targeting, scheme eligibility and grievance lifecycle rules (no database)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from app.govconnect.service import _alert_type, _priority, readiness
from app.govconnect.targeting import FarmerTarget, select_recipients
from app.grievance import service as grievance
from app.models.proactive import AlertPriority
from app.schemes.eligibility import CriteriaError, evaluate, validate_criteria


def recipients(farmers, **kw):
    args = {"district_codes": [509], "block_codes": [], "crops": [], "segment": {},
            "available_languages": {"te", "en"}, "original_language": "en", **kw}
    return {r.farmer_id: r for r in select_recipients(farmers, **args)}


def test_district_block_crop_segment_and_language() -> None:
    farmers = [
        FarmerTarget(1, "te", {509}, {509: {4600}}, {"paddy"}, 2.0),   # right block
        FarmerTarget(2, "hi", {509}, {509: set()}, set(), 1.0),        # block unknown
        FarmerTarget(3, "te", {509}, {509: {4601}}, {"paddy"}, 2.0),   # other block
        FarmerTarget(4, "te", {522}, {}, {"paddy"}, 2.0),              # other district
        FarmerTarget(5, "te", {509}, {}, {"cotton"}, 2.0),             # other crop
        FarmerTarget(6, "te", {509}, {}, {"paddy"}, 12.0),             # too large
    ]
    out = recipients(farmers, block_codes=[4600], crops=["paddy"], segment={"max_acres": 5})
    assert set(out) == {1, 2}
    assert out[1].match_level == "block" and out[2].match_level == "district"
    assert out[1].language == "te" and out[2].language == "en"  # no hi translation -> en


def test_language_falls_back_to_original_without_english() -> None:
    out = recipients([FarmerTarget(1, "hi", {509})], available_languages={"te"},
                     original_language="te")
    assert out[1].language == "te"


def test_alert_category_and_priority() -> None:
    assert _alert_type(SimpleNamespace(hazard_type="heavy_rain")).startswith("weather.")
    assert _alert_type(SimpleNamespace(hazard_type="pest_outbreak")).startswith("agronomy.")
    assert _alert_type(SimpleNamespace(hazard_type=None)) == "govt.advisory"
    assert _priority("CRITICAL") == AlertPriority.URGENT  # bypass enabled by default
    assert _priority("MEDIUM") == AlertPriority.NORMAL


def test_readiness_lists_every_problem() -> None:
    b = SimpleNamespace(title="t", body="b", authority="Unknown authority", valid_to=None,
                        district_codes=[], target_languages=["te", "hi"])
    tr = [SimpleNamespace(language="te", status="pending_review")]
    problems = readiness(b, tr)
    assert "issuing authority is required" in problems
    assert any("valid_to" in p for p in problems)
    assert "te: translation pending_review (needs officer approval)" in problems
    assert "hi: translation missing" in problems
    b.valid_to = datetime.now(UTC) - timedelta(hours=1)
    assert "valid_to is in the past" in readiness(b, tr)


CRITERIA = [
    {"id": "land", "type": "bool", "kind": "require", "rule": {"op": "eq", "value": True},
     "question": {"en": "Own land?", "te": "భూమి ఉందా?"}, "source": "guideline 1"},
    {"id": "tax", "type": "bool", "kind": "exclude", "rule": {"op": "eq", "value": True},
     "question": {"en": "Income tax?"}, "source": "guideline 2"},
    {"id": "acres", "type": "number", "kind": "require", "rule": {"op": "lte", "value": 5},
     "question": {"en": "Acres?"}, "source": "guideline 3"},
]


def test_eligibility_outcomes() -> None:
    validate_criteria(CRITERIA)
    ok = evaluate(CRITERIA, {"land": "yes", "tax": False, "acres": "2.5"})
    assert ok["status"] == "likely_eligible"
    assert evaluate(CRITERIA, {"land": True, "tax": True, "acres": 1})["failed"] == ["tax"]
    partial = evaluate(CRITERIA, {"land": True}, language="te")
    assert partial["status"] == "incomplete" and partial["criteria"][0]["question"] == "భూమి ఉందా?"
    assert evaluate(CRITERIA, {"land": "maybe", "tax": False, "acres": 1})["status"] == "incomplete"


def test_criteria_need_a_source() -> None:
    with pytest.raises(CriteriaError):
        validate_criteria([{**CRITERIA[0], "source": ""}])


class FakeSession:
    def __init__(self) -> None:
        self.added = []

    def add(self, obj) -> None:
        self.added.append(obj)
        if getattr(obj, "id", None) is None:
            obj.id = len(self.added)

    async def flush(self) -> None:
        return None


class FakeNotifier:
    def __init__(self) -> None:
        self.calls = []

    async def dispatch_alert(self, session, farmer_id, **kw):
        self.calls.append((farmer_id, kw))


async def test_grievance_lifecycle_and_sla() -> None:
    s, notifier = FakeSession(), FakeNotifier()
    t = await grievance.create_ticket(s, farmer_id=7, category="input_quality", subject="Bad seed",
                                      description="Germination failed", language="te",
                                      lgd_district_code=509, scheme_key=None, actor="farmer")
    hours = (t.sla_due_at - datetime.now(UTC)).total_seconds() / 3600
    assert 71.9 < hours <= 72
    with pytest.raises(grievance.GrievanceError):
        await grievance.change_status(s, t, "closed", "officer")  # open -> closed not allowed
    with pytest.raises(grievance.GrievanceError):
        await grievance.change_status(s, t, "rejected", "officer")  # needs a note
    await grievance.change_status(s, t, "assigned", "officer", assignee="o1", notifier=notifier)
    assert t.first_response_at is not None and notifier.calls[0][0] == 7
    await grievance.change_status(s, t, "resolved", "officer", note="Replaced", notifier=notifier)
    assert grievance.sla_state(t)["breached"] is False
    await grievance.change_status(s, t, "reopened", "farmer", note="Still bad")
    assert t.resolved_at is None and len(notifier.calls) == 2  # farmer actions don't notify
    t.sla_due_at = datetime.now(UTC) - timedelta(hours=1)
    assert grievance.sla_state(t)["breached"] is True
