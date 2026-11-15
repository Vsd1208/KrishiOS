"""Matching verified media to an answered question (F7)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.models.media import MediaAsset

MAX_ATTACHMENTS = 2


def score(asset: MediaAsset, crop: str | None, topics: set[str], language: str) -> int:
    """0 = not relevant. Crop match is required when the asset is crop-specific; topic overlap
    is required; same language ranks first."""
    asset_crops = set(asset.crops or [])
    if asset_crops and (crop is None or crop not in asset_crops):
        return 0
    overlap = len(topics & set(asset.topics or []))
    if overlap == 0:
        return 0
    return overlap * 10 + (5 if asset.language == language else 0) + (2 if asset_crops else 0)


def to_card(asset: MediaAsset) -> dict[str, Any]:
    return {"uuid": str(asset.uuid), "kind": asset.kind, "title": asset.title,
            "url": asset.url, "source_org": asset.source_org, "licence": asset.licence,
            "language": asset.language, "duration_s": asset.duration_s, "verified": True}


async def match_media(session: Any, *, crop: str | None, intent: str | None,
                      symptoms: list[str] | None, language: str) -> list[dict[str, Any]]:
    """Up to ``MAX_ATTACHMENTS`` verified assets relevant to this answer."""
    topics = {t for t in [intent, *(symptoms or [])] if t}
    if not topics:
        return []
    assets = (await session.scalars(
        select(MediaAsset).where(MediaAsset.status == "verified"))).all()
    # Equal scores: the most recently verified asset first (deterministic, freshest content).
    ranked = sorted(((score(a, crop, topics, language), a) for a in assets),
                    key=lambda p: (p[0], p[1].verified_at or p[1].created_at), reverse=True)
    return [to_card(a) for s, a in ranked if s > 0][:MAX_ATTACHMENTS]
