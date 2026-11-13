"""Catalog API: crops (multilingual) and LGD geography."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.catalog import get_crop_catalog, get_lgd_directory
from app.catalog.lgd import LGDDistrict
from app.catalog.resolver import CropEntry
from app.catalog.schemas import (
    BlockOut,
    CropChoiceOut,
    CropMentionOut,
    CropOut,
    CropResolveRequest,
    CropResolveResponse,
    DistrictOut,
)

router = APIRouter(prefix="/catalog", tags=["Catalog"])


def _crop_out(entry: CropEntry, language: str) -> CropOut:
    return CropOut(
        crop_canonical=entry.crop_canonical,
        name_en=entry.name_en,
        name_te=entry.name_te,
        name_hi=entry.name_hi,
        display_name=entry.display_name(language),
        aliases=list(entry.aliases),
        crop_group=entry.crop_group,
        domain=entry.domain,
        seasons=list(entry.seasons),
        yield_unit=entry.yield_unit,
        tier=entry.tier,
        vision_supported=entry.vision_supported,
        review_status=entry.review_status,
    )


def _district_out(d: LGDDistrict) -> DistrictOut:
    return DistrictOut(
        lgd_district_code=d.lgd_district_code,
        district_name=d.district_name,
        lgd_state_code=d.lgd_state_code,
        state_name=d.state_name,
        census_2011_code=d.census_2011_code,
    )


@router.get("/crops", response_model=list[CropOut])
async def list_crops(
    language: str = Query(default="en", pattern="^[a-z]{2}$"),
    group: str | None = None,
) -> list[CropOut]:
    """All catalog crops with names in every supported language."""
    entries = get_crop_catalog().entries()
    if group:
        entries = [e for e in entries if e.crop_group == group]
    return [_crop_out(e, language) for e in entries]


@router.get("/crops/{crop_canonical}", response_model=CropOut)
async def get_crop(crop_canonical: str, language: str = "en") -> CropOut:
    entry = get_crop_catalog().get(crop_canonical)
    if entry is None:
        raise HTTPException(status_code=404, detail="Crop not in catalog")
    return _crop_out(entry, language)


@router.post("/resolve", response_model=CropResolveResponse)
async def resolve_crop(req: CropResolveRequest) -> CropResolveResponse:
    """Resolve free text (any supported language) to catalog crops.

    ``status`` is ``resolved`` | ``ambiguous`` (show a picker) | ``multiple`` | ``not_found``.
    """
    catalog = get_crop_catalog()
    res = catalog.resolve(req.text)
    choices = []
    for key in res.candidates:
        entry = catalog.get(key)
        if entry is not None:
            choices.append(CropChoiceOut(crop_canonical=key,
                                         display_name=entry.display_name(req.language)))
    return CropResolveResponse(
        status=res.status.value,
        crop=res.crop,
        candidates=choices,
        mentions=[
            CropMentionOut(surface=m.surface, alias=m.alias, candidates=list(m.candidates))
            for m in res.mentions
        ],
    )


@router.get("/districts", response_model=list[DistrictOut])
async def find_districts(name: str, state: str | None = None,
                         prefix: bool = False) -> list[DistrictOut]:
    """Look up LGD districts by name (optionally within a state). ``prefix=true`` matches the
    start of the name (for pickers; at most 20 results)."""
    lgd = get_lgd_directory()
    if not prefix:
        return [_district_out(d) for d in lgd.find_districts(name, state)]
    from app.catalog.text import normalize  # noqa: PLC0415

    start = normalize(name)
    if len(start) < 2:  # noqa: PLR2004
        return []
    hits = [d for d in lgd.districts() if normalize(d.district_name).startswith(start)
            and (state is None or normalize(d.state_name) == normalize(state))]
    return [_district_out(d) for d in sorted(hits, key=lambda d: d.district_name)[:20]]


@router.get("/districts/{lgd_district_code}", response_model=DistrictOut)
async def get_district(lgd_district_code: int) -> DistrictOut:
    d = get_lgd_directory().district(lgd_district_code)
    if d is None:
        raise HTTPException(status_code=404, detail="Unknown LGD district code")
    return _district_out(d)


@router.get("/districts/{lgd_district_code}/blocks", response_model=list[BlockOut])
async def list_blocks(lgd_district_code: int) -> list[BlockOut]:
    return [
        BlockOut(lgd_block_code=b.lgd_block_code, block_name=b.block_name,
                 lgd_district_code=b.lgd_district_code)
        for b in get_lgd_directory().blocks_of(lgd_district_code)
    ]
