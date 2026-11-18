"""Phase 9 flows against a real Postgres (see test_phase3_db.py for the setup): photo turn ->
local vision (fake provider) -> answer with cards -> surveillance report -> outbreak draft."""

import io
import os
from datetime import UTC, datetime
from uuid import uuid4

import numpy as np
import pytest
from PIL import Image

pytestmark = pytest.mark.skipif(os.environ.get("KRISHIOS_INTEGRATION_DB") != "1",
                                reason="needs a migrated Postgres (KRISHIOS_INTEGRATION_DB=1)")


class FakeVision:
    model_name, model_version = "fake-vision", "t1"

    async def analyze(self, path, meta):
        from app.vision.providers.base import Condition, VisionResult  # noqa: PLC0415

        crop = (meta or {}).get("confirmed_crop") or "paddy"
        return VisionResult(crop_detected=crop, observations=[],
                            candidate_conditions=[Condition("blast", 0.81)],
                            model_name=self.model_name, model_version=self.model_version,
                            inference_ms=1.0, crop_candidates=[(crop, 0.93)],
                            crop_supported=True)


def _photo() -> bytes:
    rng = np.random.default_rng(0)
    img = Image.fromarray(rng.integers(30, 220, (320, 320, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_photo_turn_records_a_report_and_outbreaks_become_drafts(client, monkeypatch) -> None:
    import asyncio  # noqa: PLC0415

    from app.api.dependencies.auth import get_current_auth_context  # noqa: PLC0415
    from app.conversation import api as conversation_api  # noqa: PLC0415
    from app.conversation.manager import ConversationManager  # noqa: PLC0415
    from app.conversation.service import get_state_store  # noqa: PLC0415
    from app.main import app  # noqa: PLC0415
    from app.models.user import UserRole  # noqa: PLC0415
    from app.vision.providers import selection  # noqa: PLC0415
    from sqlalchemy import text  # noqa: PLC0415

    from tests.integration.test_phase3_db import FakeRunner  # noqa: PLC0415
    from tests.integration.test_phase4_db import _engine, as_role  # noqa: PLC0415

    monkeypatch.setattr(selection, "get_vision_provider", FakeVision)
    monkeypatch.setattr(conversation_api, "build_manager",
                        lambda sink=None: ConversationManager(store=get_state_store(),
                                                              runner=FakeRunner(), sink=sink))
    stamp = datetime.now(UTC).strftime("%H%M%S%f")
    with _engine().begin() as c:  # isolate this run's week of reports
        c.execute(text("DELETE FROM diagnosis_report WHERE source = 'photo_turn' AND "
                       "condition = 'blast' AND lgd_district_code = 509"))

    farmer = as_role(UserRole.FARMER)
    app.dependency_overrides[get_current_auth_context] = lambda: farmer
    r = client.post("/api/v1/conversation/photo-turns",
                    files={"file": ("leaf.jpg", _photo(), "image/jpeg")},
                    data={"language": "te", "district_lgd_code": "509"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "answered" and body["slots"]["crop"] == "paddy"
    assert body["vision"]["candidate_conditions"][0]["name"] == "blast"
    assert body["vision"]["official"] is False and body["providers"]["vision"]["version"] == "t1"

    with _engine().begin() as c:
        n = c.execute(text("SELECT count(*) FROM diagnosis_report WHERE lgd_district_code=509 "
                           "AND condition='blast'")).scalar_one()
        assert n == 1
        for i in range(3):  # three more farmers this week -> a possible outbreak
            c.execute(text(
                "INSERT INTO diagnosis_report (reported_at, week_start, lgd_district_code, "
                "crop_canonical, condition, confidence, crop_confirmed_by_farmer, model_version,"
                " reporter_hash, source) VALUES (now(), date_trunc('week', now())::date, 509, "
                "'paddy', 'blast', 0.8, false, 't1', :h, 'photo_turn')"),
                {"h": f"t{stamp}{i}"[:32]})

    from app.database.session import dispose_database_engine, engine  # noqa: PLC0415
    from app.worker.jobs.surveillance import outbreak_scan  # noqa: PLC0415

    async def scan() -> dict:
        try:
            return await outbreak_scan({})
        finally:
            await dispose_database_engine()  # its connections belong to this event loop

    engine.sync_engine.dispose(close=False)  # pooled connections belong to the client's loop
    res = asyncio.run(scan())
    assert res["outbreaks"] >= 1
    with _engine().begin() as c:
        draft = c.execute(text(
            "SELECT status, source_type, district_codes FROM govt_bulletin WHERE "
            "source_type='crowd' AND source_name LIKE :k ORDER BY id DESC LIMIT 1"),
            {"k": "outbreak:%:509:paddy:blast"}).one()
    assert draft.status == "needs_review" and draft.district_codes == [509]

    denied = client.get("/api/v1/surveillance/heatmap")
    assert denied.status_code == 403  # officers only
    app.dependency_overrides[get_current_auth_context] = lambda: as_role(UserRole.OFFICER,
                                                                         uuid4())
    grid = client.get("/api/v1/surveillance/heatmap?weeks=2").json()
    assert any(c["lgd_district_code"] == 509 and c["reporters"] >= 4 for c in grid["cells"])
    app.dependency_overrides.clear()
    engine.sync_engine.dispose(close=False)
