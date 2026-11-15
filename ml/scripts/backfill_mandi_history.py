"""Backfill official AGMARKNET daily prices (data.gov.in) into ``mandi_price_daily``.

One request per state per day (the key allows about 1,000 requests/day). Idempotent: rows are
upserted on (date, state, district, market, commodity, variety, grade).

Usage (from backend/, with DATA_GOV_IN_API_KEY in .env)::

    uv run python ../ml/scripts/backfill_mandi_history.py --days 45
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, timedelta

import _bootstrap  # noqa: F401


async def main(days: int, states: list[str] | None) -> None:
    from app.config.settings import get_settings
    from app.database.session import async_session_factory
    from app.live_data.market_history import sync_days

    states = states or get_settings().MANDI_HISTORY_STATES
    today = date.today()
    wanted = [today - timedelta(days=i) for i in range(days)]
    total = 0
    async with async_session_factory() as session:
        for chunk in range(0, len(wanted), 7):  # commit weekly chunks so progress is kept
            result = await sync_days(session, wanted[chunk:chunk + 7], states)
            await session.commit()
            total += result.rows
            print(f"{wanted[chunk]} .. {wanted[min(chunk + 6, len(wanted) - 1)]}: "
                  f"{result.rows} rows, failed {result.failed_days}", flush=True)
    print("total rows upserted:", total)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=45)
    ap.add_argument("--states", nargs="*")
    args = ap.parse_args()
    asyncio.run(main(args.days, args.states))
