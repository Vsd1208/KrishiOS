"""Translation API: translate, check, glossary, officer approval (auth/DB overridden)."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.api.dependencies.auth import AuthContext, get_current_auth_context
from app.auth.permissions import Permission
from app.config.settings import get_settings
from app.database.session import get_db_session
from app.main import app
from app.models.translation import TranslationRecord

SRC = "Spray Tricyclazole 75% WP at 0.6 g/L for blast in paddy."


def _auth(*perms: str) -> AuthContext:
    return AuthContext(user_uuid=uuid4(), role="OFFICER", permissions=frozenset(perms),
                       jti=uuid4())


@pytest.fixture
def session() -> AsyncMock:
    s = AsyncMock()
    s.add = MagicMock()
    return s


@pytest.fixture
def as_officer(client, session):
    app.dependency_overrides[get_current_auth_context] = lambda: _auth(
        Permission.TRANSLATION_USE, Permission.TRANSLATION_APPROVE)
    app.dependency_overrides[get_db_session] = lambda: session
    yield client
    app.dependency_overrides.clear()


def test_translate_with_mock_provider_is_labelled(as_officer, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "TRANSLATION_PROVIDER", "mock-translation")
    monkeypatch.setattr(get_settings(), "TRANSLATION_FALLBACK_PROVIDER", None)
    r = as_officer.post("/api/v1/translation/translate", json={
        "text": SRC, "source_language": "en", "target_language": "te", "severity": "HIGH"})
    body = r.json()
    assert r.status_code == 200
    assert body["provider"] == "mock-translation"
    assert body["text"].startswith("[MOCK en->te]")
    assert body["status"] == "pending_review" and body["deliverable"] is False


def test_check_endpoint_flags_changed_dose(as_officer) -> None:
    r = as_officer.post("/api/v1/translation/check",
                        json={"source": "Apply 25 kg per acre", "translation": "52 kg ఎకరానికి"})
    assert r.json()["passed"] is False and r.json()["missing_numbers"] == ["25"]


def test_glossary_is_public(client) -> None:
    body = client.get("/api/v1/translation/glossary").json()
    assert "tricyclazole" in body["protected_terms"] and "kg" in body["units"]


def test_approve_rejects_edit_that_breaks_numbers(as_officer, session) -> None:
    record = TranslationRecord(uuid=uuid4(), source_language="en", target_language="te",
                               source_text="Apply 25 kg urea per acre.",
                               translated_text="ఎకరానికి 25 kg urea వేయండి.",
                               glossary_version="x", status="pending_review", checks={},
                               attempts=[])
    session.scalar.return_value = record
    bad = as_officer.post(f"/api/v1/translation/records/{record.uuid}/approve",
                          json={"edited_text": "ఎకరానికి 50 kg urea వేయండి."})
    assert bad.status_code == 422
    ok = as_officer.post(f"/api/v1/translation/records/{record.uuid}/approve", json={})
    assert ok.status_code == 200 and ok.json()["status"] == "approved"
    assert record.approved_by is not None


def test_farmer_cannot_approve(client, session) -> None:
    app.dependency_overrides[get_current_auth_context] = lambda: _auth(Permission.TRANSLATION_USE)
    app.dependency_overrides[get_db_session] = lambda: session
    r = client.post(f"/api/v1/translation/records/{uuid4()}/approve", json={})
    app.dependency_overrides.clear()
    assert r.status_code == 403
