"""Phase 4 end-to-end flows against a real Postgres (migrated to head).

Skipped unless ``KRISHIOS_INTEGRATION_DB=1`` (see ``test_phase3_db.py`` for the setup). RAG
indexing is replaced by a recording fake (no Qdrant); translation, notification, targeting,
persistence and permissions are the production code (mock translation/TTS providers).
"""

import os
import random
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.api.dependencies.auth import AuthContext, get_current_auth_context
from app.auth.permissions import ROLE_PERMISSIONS
from app.conversation import api as conversation_api
from app.conversation.answer import AssembledAnswer
from app.conversation.manager import ConversationManager
from app.conversation.service import get_state_store
from app.govconnect import indexing
from app.main import app
from app.models.user import UserRole
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.skipif(os.environ.get("KRISHIOS_INTEGRATION_DB") != "1",
                                reason="needs a migrated Postgres (KRISHIOS_INTEGRATION_DB=1)")

BODY = ("District warning for Khammam district: orange alert. Heavy rainfall of 64.5 to 115.5 mm "
        "likely. Farmers are advised to postpone spraying on paddy and drain excess water.")


class FakeIndexer:
    def __init__(self) -> None:
        self.indexed: list[tuple[int, dict]] = []
        self.expired: list[int] = []

    async def index(self, document_id, metadata) -> bool:
        self.indexed.append((document_id, metadata))
        return True

    async def expire(self, session, document_id, when) -> bool:
        self.expired.append(document_id)
        return True


class FakeRunner:
    def __init__(self) -> None:
        self.goals: list[str] = []

    async def run(self, ctx):
        self.goals.append(ctx.goal_en)
        return AssembledAnswer(text_en="Follow the bulletin: postpone spraying.", grounded=True,
                               confidence=0.8, citations=[{"title": "bulletin"}], agents=["x"])


def _engine():
    e = os.environ
    return create_engine(f"postgresql+psycopg://{e['POSTGRES_USER']}:{e['POSTGRES_PASSWORD']}"
                         f"@{e['POSTGRES_HOST']}:{e['POSTGRES_PORT']}/{e['POSTGRES_DB']}")


def _district(c, name: str, lgd: int) -> int:
    row = c.execute(text("SELECT id FROM district WHERE lgd_district_code=:c"), {"c": lgd}).first()
    if row:
        return row[0]
    return c.execute(text(
        "INSERT INTO district (state, district_name, latitude, longitude, lgd_district_code,"
        " created_at, updated_at) VALUES ('Telangana', :n, 17.0, 80.0, :c, now(), now())"
        " RETURNING id"), {"n": name, "c": lgd}).scalar_one()


def make_farmer(lgd: int, name: str, language: str = "te") -> AuthContext:
    """A farmer row plus a linked farmer login."""
    user_uuid = uuid4()
    phone = f"9{random.randint(100000000, 999999999)}"  # noqa: S311 - test data
    with _engine().begin() as c:
        district_id = _district(c, name, lgd)
        farmer_id = c.execute(text(
            "INSERT INTO farmer (farmer_code, full_name, phone, preferred_language, district_id,"
            " village, landholding_acres, created_at, updated_at) VALUES (:code, 'Test', :p,"
            " :l, :d, 'Wyra', 2.5, now(), now()) RETURNING id"),
            {"code": uuid4(), "p": phone, "l": language, "d": district_id}).scalar_one()
        c.execute(text(
            "INSERT INTO \"user\" (uuid, phone, password_hash, role, is_active, is_verified,"
            " farmer_profile_id, created_at, updated_at) VALUES (:u, :p, 'x', 'farmer', true,"
            " true, :f, now(), now())"), {"u": user_uuid, "p": phone, "f": farmer_id})
    auth = as_role(UserRole.FARMER, user_uuid)
    auth.farmer_id = farmer_id
    return auth


def as_role(role: UserRole, user_uuid=None) -> AuthContext:
    return AuthContext(user_uuid=user_uuid or uuid4(), role=role.value,
                       permissions=frozenset(ROLE_PERMISSIONS[role]), jti=uuid4())


@pytest.fixture
def api(client, monkeypatch):
    fake = FakeIndexer()
    runner = FakeRunner()
    indexing.set_indexer(fake)
    monkeypatch.setattr(conversation_api, "build_manager",
                        lambda sink=None: ConversationManager(store=get_state_store(),
                                                              runner=runner, sink=sink))

    def login(auth: AuthContext):
        app.dependency_overrides[get_current_auth_context] = lambda: auth
        return auth

    yield client, login, fake, runner
    app.dependency_overrides.clear()
    indexing.set_indexer(None)


def _publishable(client, valid_hours: int = 48, **extra) -> dict:
    valid_to = (datetime.now(UTC) + timedelta(hours=valid_hours)).isoformat()
    r = client.post("/api/v1/govconnect/bulletins", json={
        "body": BODY, "authority": "Meteorological Centre Hyderabad (IMD)",
        "authority_level": "state", "valid_to": valid_to, "district_codes": [509],
        "target_languages": ["en", "te"], **extra})
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["severity"] == "HIGH" and b["crops"] == ["paddy"]  # extracted, not typed
    r = client.post(f"/api/v1/govconnect/bulletins/{b['uuid']}/translate")
    assert r.status_code == 200, r.text
    te = next(t for t in r.json()["translations"] if t["language"] == "te")
    assert te["status"] == "pending_review"  # HIGH severity: officer must approve
    assert any("te: translation pending_review" in p for p in r.json()["readiness"])
    r = client.post(f"/api/v1/govconnect/bulletins/{b['uuid']}/translations/te/approve", json={})
    assert r.status_code == 200, r.text
    assert r.json()["readiness"] == []
    return b


def test_publish_inbox_ask_withdraw_and_analytics(api) -> None:
    client, login, fake, runner = api
    farmer = make_farmer(509, "Khammam", "te")
    outsider = make_farmer(522, "Warangal", "te")
    officer = login(as_role(UserRole.OFFICER))
    b = _publishable(client)
    uuid = b["uuid"]

    # an edited translation that drops a number is refused
    bad = client.post(f"/api/v1/govconnect/bulletins/{uuid}/translations/te/approve",
                      json={"body": "భారీ వర్షం"})
    assert bad.status_code == 422 and bad.json()["error"]["message"]["reasons"]

    r = client.post(f"/api/v1/govconnect/bulletins/{uuid}/approve", json={})
    assert r.status_code == 200, r.text
    result = r.json()["result"]
    assert result["status"] == "published" and result["recipients"] >= 1
    assert fake.indexed and fake.indexed[-1][1]["effective_until"]  # background RAG indexing

    # published bulletins are immutable: edits must go through supersede
    assert client.patch(f"/api/v1/govconnect/bulletins/{uuid}",
                        json={"title": "x"}).status_code == 409

    login(farmer)
    inbox = client.get("/api/v1/govconnect/inbox").json()
    item = next(i for i in inbox if i["bulletin_uuid"] == uuid)
    assert item["official"] and item["language"] == "te" and item["translated"]
    assert item["state"] == "active" and item["authority"].startswith("Meteorological")
    assert client.post(f"/api/v1/govconnect/inbox/{uuid}/ack").status_code == 200
    assert client.post(f"/api/v1/govconnect/inbox/{uuid}/flag",
                       json={"reason": "unclear"}).status_code == 200
    turn = client.post("/api/v1/conversation/turns", json={
        "text": "When can I spray again?", "language": "en", "bulletin_uuid": uuid})
    assert turn.status_code == 200, turn.text
    assert "Official bulletin from Meteorological Centre" in runner.goals[-1]

    login(outsider)
    assert all(i["bulletin_uuid"] != uuid for i in client.get("/api/v1/govconnect/inbox").json())
    assert client.post(f"/api/v1/govconnect/inbox/{uuid}/ack").status_code == 404

    login(officer)
    stats = next(a for a in client.get("/api/v1/govconnect/analytics").json()
                 if a["uuid"] == uuid)
    assert stats["acknowledged"] >= 1 and stats["flagged"] >= 1 and stats["questions"] >= 1
    assert any(f["bulletin_uuid"] == uuid for f in client.get("/api/v1/govconnect/flags").json())

    r = client.post(f"/api/v1/govconnect/bulletins/{uuid}/withdraw",
                    json={"reason": "Issued for the wrong district"})
    assert r.status_code == 200 and r.json()["status"] == "withdrawn"
    assert fake.expired  # removed from RAG straight away
    actions = [a["action"] for a in client.get(f"/api/v1/govconnect/bulletins/{uuid}/audit")
               .json()]
    assert actions[:2] == ["created", "translated"] and "withdrawn" in actions

    login(farmer)
    item = next(i for i in client.get("/api/v1/govconnect/inbox").json()
                if i["bulletin_uuid"] == uuid)
    assert item["state"] == "withdrawn" and item["withdrawn_reason"]


def test_supersede_and_schedule(api) -> None:
    client, login, fake, _ = api
    make_farmer(509, "Khammam", "te")
    login(as_role(UserRole.OFFICER))
    old = _publishable(client)
    client.post(f"/api/v1/govconnect/bulletins/{old['uuid']}/approve", json={})
    new = client.post(f"/api/v1/govconnect/bulletins/{old['uuid']}/supersede").json()
    assert new["status"] == "draft" and new["supersedes"] == old["uuid"]
    client.patch(f"/api/v1/govconnect/bulletins/{new['uuid']}",
                 json={"title": "Corrected: heavy rainfall warning"})
    client.post(f"/api/v1/govconnect/bulletins/{new['uuid']}/translate")
    client.post(f"/api/v1/govconnect/bulletins/{new['uuid']}/translations/te/approve", json={})
    r = client.post(f"/api/v1/govconnect/bulletins/{new['uuid']}/approve", json={})
    assert r.json()["result"]["status"] == "published"
    assert client.get(f"/api/v1/govconnect/bulletins/{old['uuid']}").json()["status"] == \
        "superseded"
    assert fake.indexed[-1][1]["supersedes"] == old["uuid"]

    later = _publishable(client)
    when = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    r = client.post(f"/api/v1/govconnect/bulletins/{later['uuid']}/approve",
                    json={"publish_at": when})
    assert r.json()["result"]["status"] == "scheduled"


def test_locations_grievance_and_schemes(api) -> None:
    client, login, _, _ = api
    farmer = make_farmer(509, "Khammam", "te")
    login(farmer)
    from app.catalog.lgd import get_lgd_directory  # noqa: PLC0415

    lgd = get_lgd_directory()
    block = lgd.blocks_of(509)[0].lgd_block_code
    other_block = lgd.blocks_of(522)[0].lgd_block_code
    ok = client.post("/api/v1/farmers/me/locations", json={
        "label": "Paddy field", "lgd_district_code": 509, "lgd_block_code": block})
    assert ok.status_code == 201 and ok.json()["is_primary"] and ok.json()["block_name"]
    assert client.post("/api/v1/farmers/me/locations", json={
        "label": "x", "lgd_district_code": 509, "lgd_block_code": other_block}).status_code == 422

    t = client.post("/api/v1/grievances", json={
        "category": "input_quality", "subject": "Fake seed", "language": "te",
        "description": "Seeds bought at the dealer did not germinate."})
    assert t.status_code == 201, t.text
    ticket = t.json()
    assert ticket["status"] == "open" and ticket["lgd_district_code"] == 509

    login(as_role(UserRole.OFFICER))
    assert any(q["uuid"] == ticket["uuid"] for q in client.get("/api/v1/grievances/queue").json())
    client.post(f"/api/v1/grievances/queue/{ticket['uuid']}", json={"status": "assigned"})
    client.post(f"/api/v1/grievances/queue/{ticket['uuid']}",
                json={"status": "in_progress", "note": "internal", "public": False})
    r = client.post(f"/api/v1/grievances/queue/{ticket['uuid']}",
                    json={"status": "resolved", "note": "Dealer will replace the seed."})
    assert r.status_code == 200 and r.json()["breached"] is False

    login(farmer)
    mine = client.get(f"/api/v1/grievances/mine/{ticket['uuid']}").json()
    notes = [e["note"] for e in mine["events"]]
    assert "Dealer will replace the seed." in notes and "internal" not in notes
    assert client.post(f"/api/v1/grievances/mine/{ticket['uuid']}",
                       json={"action": "close"}).json()["status"] == "closed"

    # schemes: drafts are invisible to farmers until an officer verifies them
    login(as_role(UserRole.OFFICER))
    client.post("/api/v1/schemes/import-drafts")
    login(farmer)
    if client.get("/api/v1/schemes/pm_kisan").status_code == 404:
        login(as_role(UserRole.OFFICER))
        assert client.post("/api/v1/schemes/pm_kisan/verify").json()["status"] == "verified"
        login(farmer)
    scheme = client.get("/api/v1/schemes/pm_kisan?language=te").json()
    assert scheme["questions"] and "కిసాన్" in scheme["name"]
    answers = {q["id"]: False for q in scheme["questions"]} | {"owns_cultivable_land": True}
    res = client.post("/api/v1/schemes/pm_kisan/eligibility", json={"answers": answers}).json()
    assert res["status"] == "likely_eligible" and res["guidance_only"]
    answers["income_tax_payer"] = True
    res = client.post("/api/v1/schemes/pm_kisan/eligibility", json={"answers": answers}).json()
    assert res["status"] == "not_eligible" and res["failed"] == ["income_tax_payer"]
