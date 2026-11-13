"""Unit rules for assisted mode (F6) and media matching (F7); no database."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.auth.permissions import Permission
from app.extension import service as ext
from app.media.service import score
from fastapi import HTTPException


def _auth(*perms):
    return SimpleNamespace(user_uuid=uuid4(), has_permission=lambda p: p in perms)


class FakeSession:
    def __init__(self, assignment, farmer=None):
        self._a, self._f = assignment, farmer

    async def scalar(self, _query):
        return self._a

    async def get(self, _model, _id):
        return self._f


async def test_act_as_requires_permission() -> None:
    with pytest.raises(HTTPException) as e:
        await ext.check_act_as(FakeSession(None), _auth(), 1)
    assert e.value.status_code == 403


async def test_act_as_requires_assignment_and_consent() -> None:
    auth = _auth(Permission.EXTENSION_ACT_AS)
    with pytest.raises(HTTPException, match="not assigned"):
        await ext.check_act_as(FakeSession(None), auth, 1)
    pending = SimpleNamespace(consent_status="pending")
    with pytest.raises(HTTPException, match="consent"):
        await ext.check_act_as(FakeSession(pending), auth, 1)
    farmer = SimpleNamespace(id=1)
    granted = SimpleNamespace(consent_status="granted")
    assert await ext.check_act_as(FakeSession(granted, farmer), auth, 1) is farmer


def test_consent_recording_and_methods() -> None:
    a = SimpleNamespace(consent_status="pending", consent_method=None, consent_evidence=None,
                        consent_recorded_at=None)
    ext.record_consent(a, granted=True, method="signed_form", evidence="Form 12/2026")
    assert a.consent_status == "granted" and a.consent_recorded_at is not None
    ext.record_consent(a, granted=False, method="verbal_recorded", evidence=None)
    assert a.consent_status == "revoked"
    with pytest.raises(HTTPException):
        ext.record_consent(a, granted=True, method="whatsapp_thumbs_up", evidence=None)


def _asset(crops, topics, language="te"):
    return SimpleNamespace(crops=crops, topics=topics, language=language)


def test_media_score_requires_crop_and_topic_match() -> None:
    blast = _asset(["paddy"], ["disease", "spots"])
    assert score(blast, "paddy", {"disease"}, "te") > 0
    assert score(blast, "cotton", {"disease"}, "te") == 0  # wrong crop
    assert score(blast, "paddy", {"market"}, "te") == 0  # irrelevant topic
    generic = _asset([], ["weather"])
    assert score(generic, None, {"weather"}, "hi") > 0  # crop-agnostic content


def test_media_score_prefers_same_language() -> None:
    te = _asset(["paddy"], ["disease"], "te")
    hi = _asset(["paddy"], ["disease"], "hi")
    assert score(te, "paddy", {"disease"}, "te") > score(hi, "paddy", {"disease"}, "te")
