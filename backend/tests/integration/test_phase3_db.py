"""Phase 3 end-to-end flows against a real Postgres (migrated to head).

Skipped unless ``KRISHIOS_INTEGRATION_DB=1``; point POSTGRES_* at a disposable database, e.g.

    docker run -d --rm --name kos-p1-pg -e POSTGRES_PASSWORD=p1test -e POSTGRES_USER=krishios \\
        -e POSTGRES_DB=krishios_p1 -p 55432:5432 postgres:16-alpine
    POSTGRES_HOST=localhost POSTGRES_PORT=55432 POSTGRES_PASSWORD=p1test POSTGRES_DB=krishios_p1 \\
        KRISHIOS_INTEGRATION_DB=1 uv run alembic upgrade head && uv run pytest tests/integration

The agent runtime is replaced by a fake answer runner (no Qdrant/LLM needed); everything else
(NLU, catalog, translation policy, persistence, permissions) is the production code.
"""

import os
import random
from uuid import uuid4

import pytest
from app.api.dependencies.auth import AuthContext, get_current_auth_context
from app.auth.permissions import ROLE_PERMISSIONS
from app.conversation import api as conversation_api
from app.conversation.answer import AssembledAnswer
from app.conversation.manager import ConversationManager
from app.conversation.service import get_state_store
from app.main import app
from app.models.user import UserRole

pytestmark = pytest.mark.skipif(os.environ.get("KRISHIOS_INTEGRATION_DB") != "1",
                                reason="needs a migrated Postgres (KRISHIOS_INTEGRATION_DB=1)")

ANSWER = "Spray Tricyclazole 75% WP at 0.6 g/L at early blast symptoms."


class FakeRunner:
    async def run(self, ctx):
        return AssembledAnswer(text_en=ANSWER, citations=[{"title": "ICAR", "source": "ICAR"}],
                               agents=["crop_advisory_agent"], grounded=True, confidence=0.8)


def as_role(role: UserRole, user_uuid=None) -> AuthContext:
    return AuthContext(user_uuid=user_uuid or uuid4(), role=role.value,
                       permissions=frozenset(ROLE_PERMISSIONS[role]), jti=uuid4())


@pytest.fixture
def api(client, monkeypatch):
    monkeypatch.setattr(conversation_api, "build_manager",
                        lambda sink=None: ConversationManager(store=get_state_store(),
                                                              runner=FakeRunner(), sink=sink))

    def login(auth: AuthContext):
        app.dependency_overrides[get_current_auth_context] = lambda: auth
        return auth

    yield client, login
    app.dependency_overrides.clear()


def _district_id(client) -> int:
    from sqlalchemy import create_engine, text  # noqa: PLC0415

    url = (f"postgresql+psycopg://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
           f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/"
           f"{os.environ['POSTGRES_DB']}")
    eng = create_engine(url)
    with eng.begin() as c:
        row = c.execute(text("SELECT id FROM district WHERE district_name='Khammam'")).first()
        if row:
            return row[0]
        return c.execute(text(
            "INSERT INTO district (state, district_name, latitude, longitude, lgd_district_code,"
            " created_at, updated_at) VALUES ('Telangana','Khammam',17.25,80.15,509,now(),now())"
            " RETURNING id")).scalar_one()


def test_turn_persisted_feedback_and_regression_export(api) -> None:
    client, login = api
    farmer = login(as_role(UserRole.FARMER))
    r = client.post("/api/v1/conversation/turns", json={
        "text": "నా వరి పైరుకు అగ్గి తెగులు వచ్చింది, ఏమి చేయాలి?", "language": "te"})
    assert r.status_code == 200, r.text
    turn = r.json()
    assert turn["status"] == "answered" and turn["slots"]["crop"] == "paddy"

    fb = client.post("/api/v1/feedback", json={"target_type": "answer",
                                               "target_id": turn["turn_id"], "rating": "down",
                                               "reason": "unclear", "language": "te"})
    assert fb.status_code == 201, fb.text
    # another farmer cannot rate someone else's answer
    login(as_role(UserRole.FARMER))
    assert client.post("/api/v1/feedback", json={"target_type": "answer",
                                                 "target_id": turn["turn_id"],
                                                 "rating": "up"}).status_code == 404

    login(as_role(UserRole.OFFICER))
    summary = client.get("/api/v1/feedback/summary").json()
    assert summary["total"] >= 1 and summary["pending_triage"] >= 1
    intents = {b["value"]: b for b in summary["breakdown"]["intent"]}
    assert intents["disease"]["down"] >= 1
    tri = client.post(f"/api/v1/feedback/{fb.json()['uuid']}/triage",
                      json={"status": "converted_to_regression"})
    assert tri.status_code == 200
    cases = client.get("/api/v1/feedback/regression-cases").json()
    assert any(c["question"].startswith("నా వరి") and c["reason"] == "unclear" for c in cases)
    assert farmer.user_uuid  # silence unused


def test_assisted_mode_consent_act_as_and_review(api) -> None:
    client, login = api
    district_id = _district_id(client)
    worker = login(as_role(UserRole.EXTENSION_WORKER))
    phone = f"9{random.randint(100000000, 999999999)}"  # noqa: S311 - test data
    batch = client.post("/api/v1/extension/farmers/batch", json={"farmers": [
        {"full_name": "Ramu", "phone": phone, "preferred_language": "te",
         "district_id": district_id, "village": "Wyra", "landholding_acres": "2.5",
         "consent": {"granted": True, "method": "signed_form", "evidence": "Form 7"}},
        {"full_name": "Dup", "phone": phone, "preferred_language": "te",
         "district_id": district_id, "village": "Wyra", "landholding_acres": "1",
         "consent": {"granted": True, "method": "signed_form"}},
    ]})
    assert batch.status_code == 200, batch.text
    rows = batch.json()
    assert [r["status"] for r in rows] == ["created", "duplicate_phone"]
    farmer_id = rows[0]["farmer_id"]
    assert [f["farmer_id"] for f in client.get("/api/v1/extension/farmers").json()] == [farmer_id]

    turn = client.post("/api/v1/conversation/turns", json={
        "text": "paddy blast disease", "language": "te", "act_as_farmer_id": farmer_id}).json()
    queue = client.get("/api/v1/extension/review-queue").json()
    assert [q["turn_uuid"] for q in queue] == [turn["turn_id"]]  # held for worker review
    assert client.post(f"/api/v1/extension/turns/{turn['turn_id']}/share",
                       json={"share": True}).json()["shared"] is True
    assert client.get("/api/v1/extension/review-queue").json() == []

    # revoked consent blocks acting for the farmer
    client.post(f"/api/v1/extension/farmers/{farmer_id}/consent",
                json={"granted": False, "method": "verbal_recorded"})
    blocked = client.post("/api/v1/conversation/turns", json={
        "text": "paddy blast", "language": "te", "act_as_farmer_id": farmer_id})
    assert blocked.status_code == 403
    # a different worker cannot act for this farmer at all
    login(as_role(UserRole.EXTENSION_WORKER))
    assert client.post("/api/v1/conversation/turns", json={
        "text": "paddy blast", "language": "te",
        "act_as_farmer_id": farmer_id}).status_code == 403
    # farmers cannot act for others
    login(as_role(UserRole.FARMER))
    assert client.post("/api/v1/conversation/turns", json={
        "text": "paddy blast", "language": "te",
        "act_as_farmer_id": farmer_id}).status_code == 403
    assert worker.user_uuid


def test_media_needs_licence_then_attaches_to_answers(api) -> None:
    client, login = api
    login(as_role(UserRole.OFFICER))
    base = {"kind": "video", "title": f"Managing rice blast {uuid4().hex[:6]}",
            "url": "https://example.org/kvk/rice-blast", "source_org": "KVK Khammam",
            "language": "te", "crops": ["paddy"], "topics": ["disease"], "duration_s": 240}
    no_licence = client.post("/api/v1/media", json=base).json()
    assert client.post(f"/api/v1/media/{no_licence['uuid']}/verify",
                       json={"approve": True}).status_code == 422
    licensed = client.post("/api/v1/media", json={**base, "licence": "CC BY 4.0"}).json()
    assert client.post(f"/api/v1/media/{licensed['uuid']}/verify",
                       json={"approve": True}).json()["status"] == "verified"
    bad_crop = client.post("/api/v1/media", json={**base, "crops": ["not_a_crop"]})
    assert bad_crop.status_code == 422

    login(as_role(UserRole.FARMER))
    listed = client.get("/api/v1/media", params={"crop": "paddy", "topic": "disease"}).json()
    assert licensed["uuid"] in {m["uuid"] for m in listed}
    assert no_licence["uuid"] not in {m["uuid"] for m in listed}  # unverified never shown
    turn = client.post("/api/v1/conversation/turns", json={
        "text": "నా వరి పైరుకు అగ్గి తెగులు వచ్చింది", "language": "te"}).json()
    assert any(m["uuid"] == licensed["uuid"] for m in turn["media"])
    weather = client.post("/api/v1/conversation/turns", json={
        "text": "will it rain tomorrow in Khammam?", "language": "te"}).json()
    assert all(m["uuid"] != licensed["uuid"] for m in weather["media"])  # irrelevant topic
