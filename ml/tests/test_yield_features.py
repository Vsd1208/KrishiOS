"""Yield features: windows, summaries and the no-leakage guarantee (synthetic data)."""

from datetime import date, timedelta

import numpy as np
import pandas as pd

from krishios_ml.yield_features.features import build, summarise, window
from krishios_ml.yield_features.zonal import aggregate


def daily_frame(
    start: date, days: int, district: int = 509, rain: float = 5.0, tmax: float = 30.0
) -> pd.DataFrame:
    dates = [start + timedelta(days=i) for i in range(days)]
    return pd.DataFrame(
        {
            "lgd_district_code": district,
            "date": dates,
            "PRECTOTCORR": rain,
            "T2M_MAX": tmax,
            "T2M_MIN": 20.0,
            "RH2M": 70.0,
            "ALLSKY_SFC_SW_DWN": np.nan,
        }
    )


def test_windows_follow_the_season_calendar() -> None:
    assert window("Kharif", 2015, 30).start == date(2015, 4, 2)  # 60 days before 1 Jun
    assert window("Kharif", 2015, 30).cutoff == date(2015, 7, 1)
    assert window("Rabi", 2015, 0).cutoff == date(2015, 10, 1)
    assert window("Zaid", 2015, 60).cutoff == date(2016, 4, 30)  # APY 2015-16 summer = 2016


def test_no_input_on_or_after_the_cutoff_can_change_a_feature() -> None:
    """Leakage test: replace every value on/after the cutoff with extremes; features at that
    lead must be identical, and the last input date must be before the cutoff."""
    base = daily_frame(date(2015, 3, 1), 300)
    labels = pd.DataFrame({"lgd_district_code": [509], "crop_year": [2015], "season": ["Kharif"]})
    a = build(base, labels, leads=(30,))
    cutoff = a.loc[0, "cutoff"]
    poisoned = base.copy()
    late = poisoned["date"] >= cutoff
    poisoned.loc[late, ["PRECTOTCORR", "T2M_MAX"]] = [999.0, 60.0]
    b = build(poisoned, labels, leads=(30,))
    assert a.drop(columns=["last_input_date"]).equals(b.drop(columns=["last_input_date"]))
    assert a.loc[0, "last_input_date"] < cutoff


def test_summaries_and_missingness() -> None:
    d = daily_frame(date(2015, 1, 1), 10, rain=3.0, tmax=36.0)
    d.loc[d.index[:4], "PRECTOTCORR"] = 0.0  # a 4-day dry spell
    d.loc[d.index[-1], "PRECTOTCORR"] = np.nan
    s = summarise(d, expected_days=10)
    assert s["rain_sum"] == 15.0 and s["rain_days"] == 5 and s["max_dry_spell"] == 4
    assert s["rain_coverage"] == 0.9 and s["heat_days"] == 10
    assert np.isnan(s["srad_mean"]) and s["srad_mean_coverage"] == 0.0  # missing stays missing


def test_zonal_weighted_mean_ignores_missing_cells() -> None:
    values = pd.DataFrame(
        {
            "lon": [1.0, 2.0, 3.0],
            "lat": [0.0, 0.0, 0.0],
            "date": pd.to_datetime(["2015-01-01"] * 3),
            "value": [10.0, 20.0, np.nan],
        }
    )
    weights = pd.DataFrame(
        {
            "lgd_district_code": [1, 1, 1],
            "lon": [1.0, 2.0, 3.0],
            "lat": [0.0, 0.0, 0.0],
            "weight": [0.25, 0.25, 0.5],
        }
    )
    out = aggregate(values, weights)
    assert out.loc[0, "value"] == 15.0  # the missing cell's weight is not counted
