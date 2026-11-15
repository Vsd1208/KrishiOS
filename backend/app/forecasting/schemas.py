"""The YieldForecast contract (brief §"Yield provider contract").

Serving rules, re-checked on import (a file that breaks them is rejected as a whole):

- Tier C is an **abstention**: no number, no interval, ``abstain_reason`` set.
- Tier B, missing modalities or an out-of-distribution district lower the confidence and set
  ``requires_human_review``.
- A number always comes with its interval, unit and the series' normal yield.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

TIERS = ("A", "B", "C")
SEASONS = ("Kharif", "Rabi", "Zaid", "Whole Year")


class ForecastContractError(ValueError):
    """A forecast row violates the serving contract."""


@dataclass(frozen=True, slots=True)
class YieldForecast:
    lgd_district_code: int
    crop_canonical: str
    season: str
    crop_year: int
    crop_tier: str
    forecast_lead: int
    unit: str
    model_name: str
    model_version: str
    generated_at: datetime
    predicted_yield: float | None = None
    interval_low: float | None = None
    interval_high: float | None = None
    normal_yield: float | None = None
    available_modalities: list[str] = field(default_factory=list)
    missing_modalities: list[str] = field(default_factory=list)
    in_distribution: bool = True
    requires_human_review: bool = False
    abstained: bool = False
    abstain_reason: str | None = None
    district_id: int | None = None

    @property
    def change_vs_normal(self) -> float | None:
        """Forecast relative to the normal yield (-0.25 = 25% below normal)."""
        if self.abstained or not self.normal_yield or self.predicted_yield is None:
            return None
        return self.predicted_yield / self.normal_yield - 1

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["generated_at"] = self.generated_at.isoformat()
        d["change_vs_normal"] = self.change_vs_normal
        return d


def validate(f: YieldForecast) -> None:
    if f.crop_tier not in TIERS:
        raise ForecastContractError(f"unknown tier {f.crop_tier!r}")
    if f.season not in SEASONS:
        raise ForecastContractError(f"unknown season {f.season!r}")
    if f.crop_tier == "C" and not f.abstained:
        raise ForecastContractError(f"{f.crop_canonical}: tier C must abstain")
    if f.abstained:
        if f.predicted_yield is not None or f.interval_low is not None:
            raise ForecastContractError(f"{f.crop_canonical}: an abstention carries no number")
        if not f.abstain_reason:
            raise ForecastContractError(f"{f.crop_canonical}: abstention without a reason")
        return
    nums = (f.predicted_yield, f.interval_low, f.interval_high, f.normal_yield)
    if any(v is None for v in nums):
        raise ForecastContractError(f"{f.crop_canonical}: forecast without interval/normal")
    if not (0 <= f.interval_low <= f.predicted_yield <= f.interval_high):
        raise ForecastContractError(f"{f.crop_canonical}: interval does not contain forecast")
    needs_review = f.crop_tier == "B" or bool(f.missing_modalities) or not f.in_distribution
    if needs_review and not f.requires_human_review:
        raise ForecastContractError(
            f"{f.crop_canonical}: tier B / missing modality / OOD must require human review"
        )
