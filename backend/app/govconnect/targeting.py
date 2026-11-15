"""Who receives a bulletin, and in which language (pure logic + a DB loader).

Rules (ADR-020):
- **Place.** A farmer matches if their registered district or any saved location (F2) is in
  the bulletin's districts. When the bulletin names blocks, a farmer with a saved location in
  one of those blocks matches at ``block`` level; a farmer in the district whose block is
  unknown still matches at ``district`` level (better over-inform than miss a warning); a
  farmer whose known blocks in that district are all outside the list is excluded.
- **Crop.** When the bulletin names crops, farmers whose recorded crops do not overlap are
  excluded; farmers with no recorded crops are included (unknown is not "no").
- **Segment.** Optional landholding bounds (``min_acres`` / ``max_acres``).
- **Language.** The farmer's preferred language if a deliverable translation exists, else
  English, else the original language.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

LANG_ALIASES = {"te": "te", "telugu": "te", "hi": "hi", "hindi": "hi", "en": "en", "english": "en"}


def norm_language(value: str | None) -> str | None:
    return LANG_ALIASES.get((value or "").strip().lower())


@dataclass(slots=True)
class FarmerTarget:
    farmer_id: int
    language: str | None
    district_codes: set[int]
    # district code -> known block codes in that district (empty set: block unknown)
    blocks_by_district: dict[int, set[int]] = field(default_factory=dict)
    crops: set[str] = field(default_factory=set)
    acres: float | None = None


@dataclass(frozen=True, slots=True)
class Recipient:
    farmer_id: int
    language: str
    match_level: str  # block | district


def _place_match(f: FarmerTarget, districts: set[int], blocks: set[int]) -> str | None:
    hit = f.district_codes & districts
    if not hit:
        return None
    if not blocks:
        return "district"
    level = None
    for d in hit:
        known = f.blocks_by_district.get(d, set())
        if known & blocks:
            return "block"
        if not known:
            level = "district"
    return level


def select_recipients(  # noqa: PLR0913 - keyword-only targeting inputs
    farmers: list[FarmerTarget],
    *,
    district_codes: list[int],
    block_codes: list[int],
    crops: list[str],
    segment: dict[str, Any],
    available_languages: set[str],
    original_language: str,
) -> list[Recipient]:
    districts, blocks, wanted_crops = set(district_codes), set(block_codes), set(crops)
    min_acres, max_acres = segment.get("min_acres"), segment.get("max_acres")
    out: list[Recipient] = []
    for f in farmers:
        level = _place_match(f, districts, blocks)
        if level is None:
            continue
        if wanted_crops and f.crops and not (f.crops & wanted_crops):
            continue
        if f.acres is not None and (
            (min_acres is not None and f.acres < float(min_acres))
            or (max_acres is not None and f.acres > float(max_acres))
        ):
            continue
        lang = (
            f.language
            if f.language in available_languages
            else ("en" if "en" in available_languages else original_language)
        )
        out.append(Recipient(f.farmer_id, lang, level))
    return out


async def load_targets(session: AsyncSession, district_codes: list[int]) -> list[FarmerTarget]:
    """Farmers registered in, or with a saved location in, any of the districts."""
    from app.catalog.resolver import get_crop_catalog  # noqa: PLC0415
    from app.models.crop import Crop  # noqa: PLC0415
    from app.models.district import District  # noqa: PLC0415
    from app.models.farmer import Farmer  # noqa: PLC0415
    from app.models.field import Field  # noqa: PLC0415
    from app.models.field_crop import FieldCrop  # noqa: PLC0415
    from app.models.govconnect import FarmerLocation  # noqa: PLC0415

    codes = list(district_codes)
    targets: dict[int, FarmerTarget] = {}
    rows = (
        await session.execute(
            select(
                Farmer.id,
                Farmer.preferred_language,
                Farmer.landholding_acres,
                District.lgd_district_code,
            )
            .join(District, District.id == Farmer.district_id)
            .where(District.lgd_district_code.in_(codes))
        )
    ).all()
    for fid, lang, acres, code in rows:
        targets[fid] = FarmerTarget(
            fid, norm_language(lang), {code}, acres=float(acres) if acres is not None else None
        )

    locs = (
        await session.execute(
            select(
                FarmerLocation.farmer_id,
                FarmerLocation.lgd_district_code,
                FarmerLocation.lgd_block_code,
            ).where(FarmerLocation.lgd_district_code.in_(codes))
        )
    ).all()
    missing = {fid for fid, _, _ in locs} - set(targets)
    if missing:
        extra = (
            await session.execute(
                select(Farmer.id, Farmer.preferred_language, Farmer.landholding_acres).where(
                    Farmer.id.in_(missing)
                )
            )
        ).all()
        for fid, lang, acres in extra:
            targets[fid] = FarmerTarget(
                fid, norm_language(lang), set(), acres=float(acres) if acres is not None else None
            )
    for fid, d, b in locs:
        t = targets[fid]
        t.district_codes.add(d)
        known = t.blocks_by_district.setdefault(d, set())
        if b is not None:
            known.add(b)

    if targets:
        catalog = get_crop_catalog()
        crop_rows = (
            await session.execute(
                select(Field.farmer_id, Crop.crop_name)
                .join(FieldCrop, FieldCrop.field_id == Field.id)
                .join(Crop, Crop.id == FieldCrop.crop_id)
                .where(Field.farmer_id.in_(list(targets)))
            )
        ).all()
        for fid, name in crop_rows:
            key = catalog.resolve_name(name or "")
            if key:
                targets[fid].crops.add(key)
    return list(targets.values())
