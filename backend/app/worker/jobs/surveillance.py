"""``outbreak_scan`` (F8): possible outbreaks from crowdsourced photo diagnoses become
officer-review advisory drafts. No farmer is alerted by this job: an alert reaches farmers only
when an officer approves and publishes the draft through Govt Connect."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

AUTHORITY = "KrishiOS crowd photo reports (unverified model findings)"


def draft_body(district: str, crop_name: str, o: Any) -> str:
    return "\n".join([
        f"Possible outbreak: {o.condition} on {crop_name} in {district}, week of "
        f"{o.week_start:%d %b %Y}.",
        f"{o.reporters} different farmers sent photos that the KrishiOS local image model read "
        f"as {o.condition} (previous 4 weeks: {o.baseline:.1f} per week on average).",
        "These are unverified model findings from farmers' photos, NOT a diagnosis.",
        "Officers: confirm with a field visit or the KVK before publishing any advice.",
    ])


async def outbreak_scan(ctx: dict[str, Any]) -> dict[str, Any]:
    from sqlalchemy import select  # noqa: PLC0415

    from app.catalog.lgd import get_lgd_directory  # noqa: PLC0415
    from app.catalog.resolver import get_crop_catalog  # noqa: PLC0415
    from app.database.session import async_session_factory  # noqa: PLC0415
    from app.govconnect import service as gsvc  # noqa: PLC0415
    from app.models.govconnect import GovtBulletin  # noqa: PLC0415
    from app.surveillance.service import find_outbreaks, heat_grid, week_start  # noqa: PLC0415

    today = datetime.now(UTC).date()
    async with async_session_factory() as session:
        cells = await heat_grid(session, weeks=5, today=today)
        outbreaks = find_outbreaks(cells, week_start(today))
        catalog, lgd = get_crop_catalog(), get_lgd_directory()
        drafts, skipped = 0, 0
        for o in outbreaks:
            key = f"outbreak:{o.week_start}:{o.lgd_district_code}:{o.crop}:{o.condition}"[:200]
            if await session.scalar(select(GovtBulletin.id).where(
                    GovtBulletin.source_type == "crowd", GovtBulletin.source_name == key)):
                continue
            entry, ref = catalog.get(o.crop), lgd.district(o.lgd_district_code)
            crop_name = entry.name_en if entry else o.crop
            district = ref.district_name if ref else str(o.lgd_district_code)
            try:
                b = await gsvc.create_bulletin(
                    session, source_type="crowd", actor="system:outbreak_scan",
                    body=draft_body(district, crop_name, o),
                    overrides={
                        "title": f"Possible outbreak: {o.condition} on {crop_name} in {district}",
                        "authority": AUTHORITY, "authority_level": "district",
                        "district_codes": [o.lgd_district_code], "crops": [o.crop],
                        "hazard_type": "pest_disease", "severity": "MEDIUM", "source_name": key,
                        "recommended_actions": ["Verify with a field visit or KVK",
                                                "If confirmed, publish management advice"],
                    },
                )
            except gsvc.GovConnectError:  # e.g. a district code not in the LGD reference
                skipped += 1
                continue
            b.status = "needs_review"
            drafts += 1
        await session.commit()
    return {"cells": len(cells), "outbreaks": len(outbreaks), "drafts": drafts,
            "skipped": skipped}
