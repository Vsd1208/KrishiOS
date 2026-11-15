"""Govt Connect maintenance: publish scheduled bulletins, expire old ones, retry RAG work."""

from __future__ import annotations

from typing import Any


async def govconnect_maintenance(ctx: dict[str, Any]) -> dict[str, Any]:
    from app.database.session import async_session_factory  # noqa: PLC0415
    from app.govconnect.indexing import get_indexer  # noqa: PLC0415
    from app.govconnect.service import index_after_commit, run_maintenance  # noqa: PLC0415
    from app.notifications.service import NotificationService  # noqa: PLC0415

    indexer = get_indexer()
    async with async_session_factory() as session:
        out = await run_maintenance(session, notifier=NotificationService(), indexer=indexer)
        await session.commit()
    indexed = 0
    for bulletin_id in out.pop("to_index"):
        indexed += int(await index_after_commit(bulletin_id, indexer))
    return {**out, "indexed": indexed}
