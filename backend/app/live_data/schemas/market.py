"""Normalized Mandi and commodity market schemas."""

from datetime import date
from enum import Enum
from pydantic import Field

from app.live_data.schemas.common import BaseLiveDataResponse


class MandiTrend(str, Enum):
    """Commodity price trend."""

    RISING = "RISING"
    FALLING = "FALLING"
    STABLE = "STABLE"
    UNKNOWN = "UNKNOWN"


class MarketPriceObservation(BaseLiveDataResponse):
    """Normalized commodity mandi price observation."""

    commodity: str
    variety: str = "Common"
    market: str
    district: str
    state: str
    arrival_date: date
    min_price_inr_quintal: float
    max_price_inr_quintal: float
    modal_price_inr_quintal: float
    msp_inr_quintal: float | None = None
    price_trend: MandiTrend = MandiTrend.STABLE
    arrivals_tonnes: float | None = None
    currency: str = "INR"
    unit: str = "Quintal"
