"""Market data providers: the official data.gov.in Agmarknet adapter, and a labelled mock.

Reliability rules (Phase 5, ADR-023):
- MSP values come only from ``ml/reference/msp.csv``, transcribed from the PIB release with
  its URL. A crop without a row there has no MSP shown (no guessing).
- The mock never claims to be Agmarknet: it is labelled as synthetic demo data with the
  lowest authority level.
- The Agmarknet adapter needs ``DATA_GOV_IN_API_KEY``; without it, selecting it fails loudly.
"""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from typing import Any

import httpx

from app.live_data.schemas.common import FreshnessStatus, SourceAuthorityLevel
from app.live_data.schemas.market import MandiTrend, MarketPriceObservation

USER_AGENT = "KrishiOS-market/1.0"


@lru_cache(maxsize=1)
def msp_table() -> dict[str, list[dict[str, str]]]:
    """crop_canonical -> MSP rows (official, with source)."""
    from app.catalog.paths import reference_dir  # noqa: PLC0415

    path = reference_dir() / "msp.csv"
    table: dict[str, list[dict[str, str]]] = {}
    if path.exists():
        with path.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                table.setdefault(row["crop_canonical"], []).append(row)
    return table


def _crop_key(name: str) -> str | None:
    from app.catalog.resolver import get_crop_catalog  # noqa: PLC0415

    return get_crop_catalog().resolve_name(name)


def official_msp(commodity: str, variety: str | None = None) -> dict[str, Any] | None:
    """The MSP row whose grade/variety is named in the commodity or variety text (e.g.
    "Paddy(Fine/Superfine/Grade A)" -> Grade A), else the first-listed (common / medium
    staple) row, or None when the crop has no official MSP in the reference."""
    key = _crop_key(commodity.split("(", maxsplit=1)[0]) or _crop_key(commodity)
    rows = msp_table().get(key or "", [])
    if not rows:
        return None
    text = f"{commodity} {variety or ''}".lower()
    r = next(
        (row for row in rows[1:] if row["variety"] and row["variety"].lower() in text), rows[0]
    )
    return {
        "msp_inr_quintal": float(r["msp_inr_quintal"]),
        "variety": r["variety"] or None,
        "season": r["marketing_season"],
        "source_url": r["source_url"],
        "source_title": r["source_title"],
    }


class MockMarketDataProvider:
    """Synthetic prices for tests and offline demos. Clearly labelled as not official."""

    def __init__(
        self, provider_name: str = "mock-market-v1", provider_version: str = "1.0.0"
    ) -> None:
        self._provider_name = provider_name
        self._provider_version = provider_version

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def provider_version(self) -> str:
        return self._provider_version

    async def get_commodity_prices(
        self, commodity: str, state: str | None = None, district: str | None = None
    ) -> list[MarketPriceObservation]:
        now = datetime.now(UTC)
        msp = await self.get_msp(commodity)
        modal = (msp or 2000.0) * 1.02
        return [
            MarketPriceObservation(
                provider_name=self.provider_name,
                provider_version=self.provider_version,
                source="Synthetic demo prices (not official Agmarknet data)",
                authority_level=SourceAuthorityLevel.UNVERIFIED_EXTERNAL_SOURCE,
                observed_at=now,
                retrieved_at=now,
                valid_until=now + timedelta(hours=8),
                freshness=FreshnessStatus.FRESH,
                commodity=commodity.title(),
                variety="Demo",
                market=f"{district or 'Demo'} (demo)",
                district=district or "Demo",
                state=state or "Demo",
                arrival_date=date.today(),
                min_price_inr_quintal=round(modal * 0.93, 2),
                max_price_inr_quintal=round(modal * 1.08, 2),
                modal_price_inr_quintal=round(modal, 2),
                msp_inr_quintal=msp,
                price_trend=MandiTrend.STABLE,
                arrivals_tonnes=None,
            )
        ]

    async def get_msp(self, commodity: str, season: str | None = None) -> float | None:
        row = official_msp(commodity)
        return row["msp_inr_quintal"] if row else None

    async def health(self) -> bool:
        return True


def _price(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "")) if value not in (None, "", "NR") else None
    except ValueError:
        return None


def _arrival(value: str) -> date | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except (TypeError, ValueError):
            continue
    return None


class AgmarknetMarketProvider:
    """Official daily mandi prices from AGMARKNET via the data.gov.in API.

    Resource: ``DATA_GOV_IN_AGMARKNET_RESOURCE`` (daily price of commodities by market).
    Records are filtered by state and district on the server and matched to the requested crop
    through the crop catalog on our side (Agmarknet names such as "Paddy(Dhan)(Common)").
    """

    def __init__(  # noqa: PLR0913, PLR0917 - provider settings
        self,
        api_base_url: str,
        api_key: str | None,
        resource_id: str,
        provider_name: str = "agmarknet-v1",
        provider_version: str = "1.0.0",
        timeout: float = 20.0,
    ) -> None:
        if not api_key:
            from app.providers import ProviderConfigurationError  # noqa: PLC0415

            raise ProviderConfigurationError(
                "agmarknet-v1 needs DATA_GOV_IN_API_KEY (free registration on data.gov.in)"
            )
        self._base, self._key, self._resource = api_base_url.rstrip("/"), api_key, resource_id
        self._provider_name, self._provider_version, self._timeout = (
            provider_name,
            provider_version,
            timeout,
        )

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def provider_version(self) -> str:
        return self._provider_version

    async def fetch_records(
        self, state: str | None, district: str | None, limit: int = 500
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"api-key": self._key, "format": "json", "limit": limit}
        if state:
            params["filters[state]"] = state
        if district:
            params["filters[district]"] = district
        async with httpx.AsyncClient(
            timeout=self._timeout, headers={"User-Agent": USER_AGENT}
        ) as client:
            r = await client.get(f"{self._base}/{self._resource}", params=params)
            r.raise_for_status()
            return list(r.json().get("records", []))

    async def get_commodity_prices(
        self, commodity: str, state: str | None = None, district: str | None = None
    ) -> list[MarketPriceObservation]:
        wanted = _crop_key(commodity)
        now = datetime.now(UTC)
        out = []
        for rec in await self.fetch_records(state, district):
            name = str(rec.get("commodity", ""))
            key = _crop_key(name.split("(", maxsplit=1)[0]) or _crop_key(name)
            if wanted is None or key != wanted:
                continue
            modal, lo, hi = (_price(rec.get(k)) for k in ("modal_price", "min_price", "max_price"))
            arrived = _arrival(str(rec.get("arrival_date", "")))
            if modal is None or arrived is None:
                continue  # incomplete official rows are dropped, never filled in
            age = (date.today() - arrived).days
            out.append(
                MarketPriceObservation(
                    provider_name=self.provider_name,
                    provider_version=self.provider_version,
                    source="AGMARKNET (DMI, MoA&FW) via data.gov.in",
                    authority_level=SourceAuthorityLevel.GOVERNMENT,
                    observed_at=datetime.combine(arrived, datetime.min.time(), tzinfo=UTC),
                    retrieved_at=now,
                    valid_until=now + timedelta(hours=12),
                    freshness=FreshnessStatus.FRESH if age <= 2 else FreshnessStatus.STALE,  # noqa: PLR2004
                    commodity=name,
                    variety=str(rec.get("variety") or "—"),
                    market=str(rec.get("market", "")),
                    district=str(rec.get("district", "")),
                    state=str(rec.get("state", "")),
                    arrival_date=arrived,
                    min_price_inr_quintal=lo if lo is not None else modal,
                    max_price_inr_quintal=hi if hi is not None else modal,
                    modal_price_inr_quintal=modal,
                    msp_inr_quintal=(official_msp(name, str(rec.get("variety") or "")) or {}).get(
                        "msp_inr_quintal"
                    ),
                )
            )
        return sorted(out, key=lambda o: o.arrival_date, reverse=True)

    async def get_msp(self, commodity: str, season: str | None = None) -> float | None:
        row = official_msp(commodity)
        return row["msp_inr_quintal"] if row else None

    async def health(self) -> bool:
        return True
