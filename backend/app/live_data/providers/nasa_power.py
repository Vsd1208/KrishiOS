"""NASA POWER daily agro-meteorology (independent cross-check source, Phase 5).

API: ``https://power.larc.nasa.gov/api/temporal/daily/point`` (no key; NASA data, free use with
attribution). Values are satellite/reanalysis based (MERRA-2 / GEOS-IT), lag about 2 days, and
use ``-999`` as the fill value, which is returned as missing, never as a number.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx

BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
USER_AGENT = "KrishiOS-weather/1.0"
FILL = -999.0


class NasaPowerClient:
    provider_name = "nasa-power-daily"
    attribution = "NASA POWER (power.larc.nasa.gov)"

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    async def daily(self, latitude: float, longitude: float, start: date,
                    end: date) -> dict[str, dict[str, float | None]]:
        """``{"2026-11-10": {"precip_mm": 0.0, "tmax_c": 28.3, "tmin_c": 16.3}, ...}``"""
        params = {"parameters": "PRECTOTCORR,T2M_MAX,T2M_MIN", "community": "AG",
                  "latitude": round(latitude, 4), "longitude": round(longitude, 4),
                  "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"),
                  "format": "JSON"}
        async with httpx.AsyncClient(timeout=self._timeout,
                                     headers={"User-Agent": USER_AGENT}) as client:
            r = await client.get(BASE_URL, params=params)
            r.raise_for_status()
            data: dict[str, Any] = r.json()
        p = data["properties"]["parameter"]
        out: dict[str, dict[str, float | None]] = {}
        for key, name in (("PRECTOTCORR", "precip_mm"), ("T2M_MAX", "tmax_c"),
                          ("T2M_MIN", "tmin_c")):
            for day, value in p.get(key, {}).items():
                iso = f"{day[:4]}-{day[4:6]}-{day[6:]}"
                out.setdefault(iso, {})[name] = None if value is None or value <= FILL else value
        return out
