"""``forecast_import``: import the newest batch forecast artifact, then turn likely shortfalls
into (a) ``agronomy.yield_shortfall_forecast`` events for farmers in that district and (b) one
officer-review advisory draft per district and season. Nothing is published automatically:
the draft goes through the normal Govt Connect review, translation and approval."""

from __future__ import annotations

from typing import Any

from app.worker.jobs.base import JobSkipped

AUTHORITY = "KrishiOS Yield Intelligence (model estimate, not an official figure)"


def _fmt(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.2f}"


def draft_body(district: str, season: str, crop_year: int, rows: list[Any], names: dict) -> str:
    lines = [
        f"Yield outlook for {district}, {season} {crop_year}-{str(crop_year + 1)[-2:]} "
        "(model estimate, NOT an official crop-cutting, YES-TECH or insurance figure).",
        "The forecast suggests yields well below normal for:",
    ]
    for r in rows:
        pct = 1 - r.predicted_yield / r.normal_yield
        lines.append(
            f"- {names.get(r.crop_canonical, r.crop_canonical)}: {_fmt(r.predicted_yield)} "
            f"{r.unit} (normal {_fmt(r.normal_yield)}; likely range {_fmt(r.interval_low)}-"
            f"{_fmt(r.interval_high)}), about {pct:.0%} below normal"
            + (" [tier B: wide uncertainty]" if r.crop_tier == "B" else "")
        )
    r0 = rows[0]
    lines.append(
        f"Model {r0.model_name} {r0.model_version}, lead {r0.forecast_lead} days, generated "
        f"{r0.generated_at:%Y-%m-%d}. Officers: verify with field reports before publishing."
    )
    return "\n".join(lines)


async def forecast_import(ctx: dict[str, Any]) -> dict[str, Any]:
    from sqlalchemy import select  # noqa: PLC0415

    from app.catalog.lgd import get_lgd_directory  # noqa: PLC0415
    from app.catalog.paths import artifacts_dir  # noqa: PLC0415
    from app.catalog.resolver import get_crop_catalog  # noqa: PLC0415
    from app.database.session import async_session_factory  # noqa: PLC0415
    from app.events.contracts import EventEnvelope, EventType  # noqa: PLC0415
    from app.forecasting import service as fsvc  # noqa: PLC0415
    from app.forecasting.importer import import_artifact, latest_artifact  # noqa: PLC0415
    from app.govconnect import service as gsvc  # noqa: PLC0415
    from app.models.district import District  # noqa: PLC0415
    from app.models.farmer import Farmer  # noqa: PLC0415
    from app.models.govconnect import GovtBulletin  # noqa: PLC0415
    from app.proactive.api.dependencies import get_event_processor  # noqa: PLC0415

    artifact = latest_artifact(artifacts_dir() / "forecasts")
    if artifact is None:
        raise JobSkipped("no forecast artifact under ML_ARTIFACTS_DIR/forecasts")
    async with async_session_factory() as session:
        result = await import_artifact(session, artifact)
        await session.commit()
        if not result.imported:
            return {"imported": False, "model_version": result.model_version,
                    "reason": result.reason}
        short = await fsvc.shortfalls(session, result.import_id)
        catalog = get_crop_catalog()
        names = {e.crop_canonical: e.name_en for e in catalog.entries()}
        districts = {d.lgd_district_code: d for d in (await session.scalars(
            select(District).where(District.lgd_district_code.in_(
                {r.lgd_district_code for r in short} or {-1})))).all()}
        with_farmers = set((await session.scalars(
            select(District.lgd_district_code).join(Farmer, Farmer.district_id == District.id)
            .distinct())).all())
        processor = get_event_processor(session=session)
        events = drafts = 0
        groups: dict[tuple[int, str, int], list[Any]] = {}
        for r in short:
            groups.setdefault((r.lgd_district_code, r.season, r.crop_year), []).append(r)
            d = districts.get(r.lgd_district_code)
            if d is None or r.lgd_district_code not in with_farmers:
                continue
            await processor.process_event(session, EventEnvelope(
                event_type=EventType.YIELD_SHORTFALL_FORECAST.value,
                source="forecast_import",
                payload={
                    "district": d.district_name, "state": d.state,
                    "lgd_district_code": r.lgd_district_code,
                    "crop_canonical": r.crop_canonical, "season": r.season,
                    "crop_year": r.crop_year, "crop_tier": r.crop_tier,
                    "predicted_yield": r.predicted_yield, "normal_yield": r.normal_yield,
                    "interval_low": r.interval_low, "interval_high": r.interval_high,
                    "unit": r.unit, "shortfall_pct": 1 - r.predicted_yield / r.normal_yield,
                    "requires_human_review": r.requires_human_review,
                    "model_version": r.model_version, "forecast_lead": r.forecast_lead,
                    "abstained": False,
                },
            ))
            events += 1
        for (lgd, season, year), rows in groups.items():
            key = f"yield:{result.model_version}:{lgd}:{season}:{year}"
            exists = await session.scalar(select(GovtBulletin.id).where(
                GovtBulletin.source_type == "forecast", GovtBulletin.source_name == key))
            if exists:
                continue
            d = districts.get(lgd)
            ref = get_lgd_directory().district(lgd)
            dname = d.district_name if d else (ref.district_name if ref else str(lgd))
            b = await gsvc.create_bulletin(
                session, source_type="forecast", actor="system:forecast_import",
                body=draft_body(dname, season, year, rows, names),
                overrides={
                    "title": f"Yield outlook: likely shortfall in {dname} ({season} {year})",
                    "authority": AUTHORITY, "authority_level": "district",
                    "district_codes": [lgd], "crops": sorted({r.crop_canonical for r in rows}),
                    "hazard_type": "yield_shortfall", "severity": "MEDIUM",
                    "source_name": key,
                    "recommended_actions": [
                        "Verify with crop condition and field reports",
                        "Advise contingency measures if confirmed",
                        "Remind farmers of PMFBY crop-loss intimation timelines",
                    ],
                },
            )
            b.status = "needs_review"  # model output is never published without review
            drafts += 1
        await session.commit()
    return {"imported": True, "model_version": result.model_version, "rows": result.rows,
            "shortfalls": len(short), "events": events, "drafts": drafts}
