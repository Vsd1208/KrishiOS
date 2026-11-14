"""Weather feed: cross-check verdicts, event thresholds and the spray rule (no network)."""

from datetime import date

from app.govconnect.weather_feed import FeedDistrict, events_for
from app.live_data.providers.weather_provider import spray_window
from app.live_data.schemas.weather import DailyForecastItem
from app.live_data.services.crosscheck import compare


def day(d: str, rain: float, tmax: float, prob: float = 80, wind: float = 2) -> DailyForecastItem:
    return DailyForecastItem(date=d, temperature_min_celsius=20, temperature_max_celsius=tmax,
                             precipitation_probability_percent=prob, precipitation_sum_mm=rain,
                             max_wind_speed_mps=wind, weather_condition="x")


def series(vals):
    return {f"2026-11-{i + 1:02d}": {"precip_mm": r, "tmax_c": t} for i, (r, t) in enumerate(vals)}


def test_crosscheck_agree_disagree_unverified() -> None:
    a = series([(0, 30), (5, 31), (0, 29), (2, 30)])
    assert compare(a, series([(0, 29), (6, 30), (0, 30), (1, 31)]),
                   primary_name="om", reference_name="nasa").status == "agree"
    hot = compare(a, series([(0, 35), (5, 36), (0, 34), (2, 35)]),
                  primary_name="om", reference_name="nasa")
    assert hot.status == "disagree" and "max temperature" in hot.reasons[0]
    wet = compare(a, series([(30, 30), (25, 31), (0, 29), (2, 30)]),
                  primary_name="om", reference_name="nasa")
    assert wet.status == "disagree" and "rainfall" in wet.reasons[0]
    missing = {k: {"precip_mm": None, "tmax_c": None} for k in a}
    assert compare(a, missing, primary_name="om", reference_name="nasa").status == "unverified"


def test_events_only_above_rule_thresholds_within_three_days() -> None:
    d = FeedDistrict(509, "Khammam", "Telangana", 17.25, 80.15)
    days = [day("2026-11-14", 55, 33), day("2026-11-15", 10, 40), day("2026-11-18", 90, 30)]
    ev = events_for(d, days, "agree", date(2026, 11, 14))
    kinds = [(e.event_type, e.payload["date"]) for e in ev]
    assert kinds == [("weather.heavy_rain", "2026-11-14"), ("weather.extreme_heat", "2026-11-15")]
    rain = ev[0].payload
    assert rain["probability"] == 0.8 and rain["official"] is False
    assert rain["crosscheck"] == "agree"
    assert rain["district"] == "Khammam"


def test_spray_window_uses_the_forecast() -> None:
    assert spray_window(day("d", 0, 30, prob=10, wind=2))[0] is True
    windy, reason = spray_window(day("d", 0, 30, prob=10, wind=6))
    assert windy is False and "km/h" in reason
    assert spray_window(day("d", 5, 30, prob=70, wind=2))[0] is False
    assert spray_window(None) == (False, "No forecast available; spray window unknown.")
