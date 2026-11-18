"""CropIdentifyTool flags uncertain crops; outbreak detection needs distinct reporters."""

from datetime import date
from types import SimpleNamespace

from app.agents.tools.crop_identify import CropIdentifyTool
from app.database import session as db
from app.govconnect import service as gsvc
from app.surveillance import service
from app.surveillance.service import find_outbreaks, reporter_hash, week_start
from app.vision.providers.base import Condition, VisionResult
from app.worker.jobs.surveillance import outbreak_scan


class Provider:
    def __init__(self, supported):
        self.supported = supported

    async def analyze(self, path, meta):
        return VisionResult(crop_detected="tomato" if self.supported else None,
                            observations=[], candidate_conditions=[Condition("early blight", 0.7)],
                            model_name="m", model_version="v", inference_ms=1.0,
                            crop_candidates=[("tomato", 0.9 if self.supported else 0.4)],
                            crop_supported=self.supported)


async def test_tool_marks_uncertain_crops_for_confirmation(tmp_path) -> None:
    img = tmp_path / "x.jpg"
    img.write_bytes(b"x")
    ok = await CropIdentifyTool(Provider(True)).execute({"image_path": str(img)})
    unsure = await CropIdentifyTool(Provider(False)).execute({"image_path": str(img)})
    assert ok.success and not ok.data["needs_confirmation"] and ok.data["official"] is False
    assert unsure.data["needs_confirmation"]
    missing = await CropIdentifyTool(Provider(True)).execute({"image_path": "nope.jpg"})
    assert not missing.success


def cell(week: date, n: int, cond="blast") -> dict:
    return {"lgd_district_code": 509, "crop": "paddy", "condition": cond,
            "week_start": week.isoformat(), "reporters": n}


def test_outbreak_needs_enough_reporters_and_a_jump_over_baseline() -> None:
    w = week_start(date(2026, 11, 16))
    prev = [cell(date.fromordinal(w.toordinal() - 7 * i), 1) for i in range(1, 5)]
    assert [o.reporters for o in find_outbreaks([*prev, cell(w, 4)], w, 3, 2.0)] == [4]
    assert find_outbreaks([*prev, cell(w, 2)], w, 3, 2.0) == []  # too few farmers
    steady = [cell(date.fromordinal(w.toordinal() - 7 * i), 3) for i in range(1, 5)]
    assert find_outbreaks([*steady, cell(w, 4)], w, 3, 2.0) == []  # no jump over baseline


async def test_one_invalid_outbreak_does_not_lose_the_other_drafts(monkeypatch) -> None:
    class Session:
        committed = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def scalar(self, stmt):
            return None

        async def commit(self):
            self.committed = True

    async def grid(session, weeks, today):
        return []

    created = []

    async def create(session, **kw):
        if kw["overrides"]["district_codes"] == [999999]:
            raise gsvc.GovConnectError(422, "unknown LGD district code")
        created.append(kw["overrides"]["district_codes"])
        return SimpleNamespace(status="draft")

    week = date(2026, 11, 16)
    found = [service.Outbreak(999999, "paddy", "blast", week, 5, 0.0),
             service.Outbreak(509, "paddy", "blast", week, 4, 0.0)]
    db_session = Session()
    monkeypatch.setattr(db, "async_session_factory", lambda: db_session)
    monkeypatch.setattr(service, "heat_grid", grid)
    monkeypatch.setattr(service, "find_outbreaks", lambda cells, w: found)
    monkeypatch.setattr(gsvc, "create_bulletin", create)
    res = await outbreak_scan({})
    assert res["drafts"] == 1 and res["skipped"] == 1
    assert created == [[509]] and db_session.committed


def test_reporter_hash_is_stable_and_not_the_user_id() -> None:
    assert reporter_hash("u-1") == reporter_hash("u-1") != reporter_hash("u-2")
    assert "u-1" not in reporter_hash("u-1") and len(reporter_hash("u-1")) == 32
