"""Cross-check recent weather between two independent sources (Phase 5, ADR-023).

The forecast comes from one model (Open-Meteo). Its own values for the last few days are
compared with NASA POWER on the days both have data. Agreement does not prove the forecast
right, but disagreement is a reason to show lower confidence and say so.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

TMAX_TOLERANCE_C = 2.5
RAIN_ABS_TOLERANCE_MM = 10.0
RAIN_REL_TOLERANCE = 0.3
MIN_DAYS = 3


@dataclass(slots=True)
class CrossCheck:
    status: str  # agree | disagree | unverified
    days_compared: int
    tmax_mae_c: float | None
    rain_total_primary_mm: float | None
    rain_total_reference_mm: float | None
    reasons: list[str]
    primary: str
    reference: str

    def to_dict(self) -> dict:
        return asdict(self)


def compare(primary: dict[str, dict[str, float | None]],
            reference: dict[str, dict[str, float | None]], *, primary_name: str,
            reference_name: str) -> CrossCheck:
    days = sorted(d for d in primary if d in reference
                  and primary[d].get("tmax_c") is not None
                  and reference[d].get("tmax_c") is not None
                  and primary[d].get("precip_mm") is not None
                  and reference[d].get("precip_mm") is not None)
    if len(days) < MIN_DAYS:
        return CrossCheck("unverified", len(days), None, None, None,
                          [f"only {len(days)} overlapping days (need {MIN_DAYS})"],
                          primary_name, reference_name)
    mae = sum(abs(primary[d]["tmax_c"] - reference[d]["tmax_c"]) for d in days) / len(days)
    rain_p = sum(primary[d]["precip_mm"] for d in days)
    rain_r = sum(reference[d]["precip_mm"] for d in days)
    reasons = []
    if mae > TMAX_TOLERANCE_C:
        reasons.append(f"max temperature differs by {mae:.1f} °C on average")
    if abs(rain_p - rain_r) > max(RAIN_ABS_TOLERANCE_MM, RAIN_REL_TOLERANCE * max(rain_p, rain_r)):
        reasons.append(f"rainfall totals differ ({rain_p:.0f} vs {rain_r:.0f} mm)")
    return CrossCheck("disagree" if reasons else "agree", len(days), round(mae, 2),
                      round(rain_p, 1), round(rain_r, 1), reasons, primary_name, reference_name)
