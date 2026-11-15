"""Seed reference data into Postgres (idempotent).

* Upserts ``crop_catalog`` from ``ml/reference/crop_catalog.csv``.
* Backfills ``district.lgd_district_code`` / ``lgd_state_code`` / ``census_2011_code`` for
  existing districts whose (state, name) match LGD uniquely; reports the rest for review.
* Backfills ``crop.catalog_canonical`` where the crop name resolves uniquely.

Usage (inside the backend container or with a local DB)::

    uv run python -m scripts.seed_reference_data
"""

from __future__ import annotations

import asyncio

from loguru import logger
from sqlalchemy import select

from app.catalog import get_crop_catalog, get_lgd_directory
from app.catalog.models import CropCatalogEntry
from app.database.session import async_session_factory
from app.models.crop import Crop
from app.models.district import District


async def seed() -> dict[str, int]:
    catalog = get_crop_catalog()
    lgd = get_lgd_directory()
    stats = {"catalog_upserts": 0, "districts_linked": 0, "districts_unmatched": 0,
             "crops_linked": 0, "crops_unmatched": 0}
    async with async_session_factory() as session:
        existing = {
            row.crop_canonical: row
            for row in (await session.scalars(select(CropCatalogEntry))).all()
        }
        for e in catalog.entries():
            row = existing.get(e.crop_canonical) or CropCatalogEntry(crop_canonical=e.crop_canonical)
            row.name_en, row.name_te, row.name_hi = e.name_en, e.name_te, e.name_hi
            row.aliases, row.seasons, row.apy_names = list(e.aliases), list(e.seasons), list(
                e.apy_names
            )
            row.scientific_name = e.scientific_name or None
            row.crop_group, row.domain, row.yield_unit = e.crop_group, e.domain, e.yield_unit
            row.tier, row.vision_supported = e.tier, e.vision_supported
            row.review_status = e.review_status
            session.add(row)
            stats["catalog_upserts"] += 1

        for district in (await session.scalars(select(District))).all():
            if district.lgd_district_code is not None:
                continue
            match = lgd.resolve_district(district.district_name, district.state)
            if match is None:
                stats["districts_unmatched"] += 1
                logger.warning("No unique LGD match | state={} | district={}",
                               district.state, district.district_name)
                continue
            district.lgd_district_code = match.lgd_district_code
            district.lgd_state_code = match.lgd_state_code
            district.census_2011_code = match.census_2011_code
            stats["districts_linked"] += 1

        for crop in (await session.scalars(select(Crop))).all():
            if crop.catalog_canonical:
                continue
            key = catalog.resolve_name(crop.crop_name)
            if key is None:
                stats["crops_unmatched"] += 1
                logger.warning("Crop not in catalog | crop_name={}", crop.crop_name)
                continue
            crop.catalog_canonical = key
            stats["crops_linked"] += 1
        await session.commit()
    logger.info("Reference seed complete | {}", stats)
    return stats


if __name__ == "__main__":
    asyncio.run(seed())
