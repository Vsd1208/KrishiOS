"""Yield Intelligence: serving contract, importer checks, shortfall logic, proactive rule."""

import hashlib
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.events.contracts import EventEnvelope, EventType
from app.forecasting.importer import import_artifact
from app.forecasting.schemas import ForecastContractError, YieldForecast, validate
from app.forecasting.service import is_shortfall
from app.models.proactive import RiskSeverity
from app.proactive.rules.agricultural_rules import YieldShortfallRule
from app.worker.jobs.forecasting import draft_body

GEN = datetime(2026, 11, 15, tzinfo=UTC)


def fc(**kw) -> YieldForecast:
    base = dict(lgd_district_code=509, crop_canonical="paddy", season="Rabi", crop_year=2026,
                crop_tier="A", forecast_lead=30, unit="Tonnes/Hectare", model_name="b3",
                model_version="v1", generated_at=GEN, predicted_yield=3.0, interval_low=2.4,
                interval_high=3.6, normal_yield=3.5,
                available_modalities=["weather", "yield_history"])
    return YieldForecast(**{**base, **kw})


def test_valid_tier_a_forecast_passes() -> None:
    validate(fc())
    assert round(fc().change_vs_normal, 4) == round(3.0 / 3.5 - 1, 4)


@pytest.mark.parametrize("bad, msg", [
    (dict(crop_tier="C"), "tier C must abstain"),
    (dict(abstained=True, abstain_reason="insufficient data"), "carries no number"),
    (dict(crop_tier="B"), "require human review"),
    (dict(in_distribution=False), "require human review"),
    (dict(missing_modalities=["weather"]), "require human review"),
    (dict(interval_high=2.9), "does not contain"),
    (dict(normal_yield=None), "without interval/normal"),
])
def test_contract_violations_are_rejected(bad, msg) -> None:
    with pytest.raises(ForecastContractError, match=msg):
        validate(fc(**bad))


def test_tier_c_abstention_is_valid_without_numbers() -> None:
    validate(fc(crop_tier="C", abstained=True, abstain_reason="insufficient data",
                predicted_yield=None, interval_low=None, interval_high=None, normal_yield=None))


def _artifact(tmp_path, rows, tamper=False):
    data = "\n".join(json.dumps(r.to_dict()) for r in rows).encode()
    (tmp_path / "forecasts.jsonl").write_bytes(data + (b" " if tamper else b""))
    (tmp_path / "manifest.json").write_text(json.dumps({
        "model_name": "b3", "model_version": "v1", "generated_at": GEN.isoformat(),
        "file": "forecasts.jsonl", "sha256": hashlib.sha256(data).hexdigest(),
        "rows": len(rows)}))
    return tmp_path


def _session():
    s = MagicMock()
    s.scalar = AsyncMock(return_value=None)
    s.flush = AsyncMock()
    return s


async def test_import_rejects_a_tampered_file(tmp_path) -> None:
    with pytest.raises(ForecastContractError, match="hash"):
        await import_artifact(_session(), _artifact(tmp_path, [fc()], tamper=True))


async def test_import_is_all_or_nothing(tmp_path) -> None:
    s = _session()
    bad = fc(crop_canonical="ragi", crop_tier="C")  # number on a tier C row
    with pytest.raises(ForecastContractError):
        await import_artifact(s, _artifact(tmp_path, [fc(), bad]))
    s.add.assert_not_called()


async def test_import_adds_every_row_once(tmp_path) -> None:
    s = _session()
    res = await import_artifact(s, _artifact(tmp_path, [fc(), fc(crop_canonical="cotton")]))
    assert res.imported and res.rows == 2
    assert s.add.call_count == 3  # import record + 2 rows
    s.scalar = AsyncMock(return_value=SimpleNamespace(rows=2, id=7))
    again = await import_artifact(s, _artifact(tmp_path, [fc(), fc(crop_canonical="cotton")]))
    assert not again.imported and again.reason == "already imported"


def rec(**kw):
    base = dict(abstained=False, predicted_yield=2.5, normal_yield=3.5, interval_high=3.2)
    return SimpleNamespace(**{**base, **kw})


def test_shortfall_needs_both_size_and_confidence() -> None:
    assert is_shortfall(rec(), pct=0.2)  # 29% below, upper bound below normal
    assert not is_shortfall(rec(interval_high=3.8), pct=0.2)  # interval reaches normal
    assert not is_shortfall(rec(predicted_yield=3.0), pct=0.2)  # only 14% below
    assert not is_shortfall(rec(abstained=True, predicted_yield=None), pct=0.2)


def _event(**kw):
    payload = {"crop_canonical": "paddy", "district": "Khammam", "season": "Rabi",
               "crop_tier": "A", "shortfall_pct": 0.4, "requires_human_review": False, **kw}
    return EventEnvelope(event_type=EventType.YIELD_SHORTFALL_FORECAST.value, payload=payload)


async def test_rule_matches_only_the_farmers_crop() -> None:
    rule = YieldShortfallRule()
    hit = await rule.evaluate(_event(), {"crop": "Rice"})  # alias resolves to paddy
    assert hit.matched and hit.severity is RiskSeverity.HIGH
    assert "not an official" in hit.recommended_action_summary
    miss = await rule.evaluate(_event(), {"crop": "Cotton"})
    assert not miss.matched
    assert not (await rule.evaluate(_event(crop_tier="C"), {"crop": "Paddy"})).matched
    medium = await rule.evaluate(_event(shortfall_pct=0.22), {"crop": "Paddy"})
    assert medium.severity is RiskSeverity.MEDIUM


def test_draft_says_it_is_not_an_official_figure() -> None:
    r = SimpleNamespace(crop_canonical="paddy", predicted_yield=2.5, normal_yield=3.5,
                        interval_low=2.0, interval_high=3.2, unit="Tonnes/Hectare",
                        crop_tier="B", model_name="b3", model_version="v1", forecast_lead=30,
                        generated_at=GEN)
    body = draft_body("Khammam", "Rabi", 2026, [r], {"paddy": "Paddy (Rice)"})
    assert "NOT an official" in body and "Rabi 2026-27" in body
    assert "29% below normal" in body and "tier B" in body


async def test_yield_tool_resolves_aliases_and_marks_unofficial() -> None:
    from app.agents.tools.yield_forecast import YieldForecastTool

    async def lookup(lgd, crop, season):
        return {**fc(crop_canonical=crop).to_dict()}

    r = await YieldForecastTool(lookup).execute({"crop": "rice", "lgd_district_code": 509})
    assert r.success and r.data["crop_canonical"] == "paddy" and r.data["official"] is False
    bad = await YieldForecastTool(lookup).execute({"crop": "unobtainium", "lgd_district_code": 1})
    assert not bad.success
