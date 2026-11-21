"""Yield features: windows, summaries and the no-leakage guarantee (synthetic data)."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

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
    cutoff = a.loc[0, "cutoff"].date()
    poisoned = base.copy()
    late = poisoned["date"] >= cutoff
    poisoned.loc[late, ["PRECTOTCORR", "T2M_MAX"]] = [999.0, 60.0]
    b = build(poisoned, labels, leads=(30,))
    assert a.drop(columns=["last_input_date"]).equals(b.drop(columns=["last_input_date"]))
    assert a.loc[0, "last_input_date"] < a.loc[0, "cutoff"]
    assert a.loc[0, "last_input_date"].date() == date(2015, 6, 30)  # the day before cutoff


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


def test_eastern_rice_is_annual_production_over_area() -> None:
    from krishios_ml.yield_labels.dataset import annual_rice

    df = pd.DataFrame(
        {
            "lgd_district_code": [1, 1, 2],
            "district_name": ["a", "a", "b"],
            "lgd_state_code": [18, 18, 28],
            "state_name": ["Assam", "Assam", "Andhra Pradesh"],
            "crop_canonical": ["paddy"] * 3,
            "season": ["Kharif", "Zaid", "Kharif"],
            "crop_year": [2010] * 3,
            "area_ha": [100.0, 300.0, 50.0],
            "production": [100.0, 900.0, 150.0],
            "yield": [1.0, 3.0, 3.0],
            "yield_unit": ["t/ha"] * 3,
        }
    )
    out = annual_rice(df)
    assam = out[out["lgd_district_code"] == 1]
    assert len(assam) == 1 and assam["season"].iloc[0] == "Whole Year"
    assert assam["yield"].iloc[0] == 2.5  # 1000 t / 400 ha, not the mean of yields (2.0)
    assert assam["seasons_combined"].iloc[0] == "Kharif+Zaid"
    assert out[out["lgd_district_code"] == 2]["season"].tolist() == ["Kharif"]  # other states


def test_each_parameter_uses_its_own_grid(tmp_path) -> None:
    """Solar radiation is on POWER's 1° grid: aggregating it with MERRA-2 weights silently
    dropped ~72% of district-days once, so a weighted cell absent from the data must raise."""
    import pytest

    from krishios_ml.yield_features.zonal import build_daily, grid_of

    assert grid_of("ALLSKY_SFC_SW_DWN") == "ceres1deg" and grid_of("T2M_MAX") == "merra2"
    day = pd.to_datetime(["2015-01-01"])
    pd.DataFrame({"lon": [80.5], "lat": [17.5], "date": day, "value": [20.0]}).to_parquet(
        tmp_path / "ALLSKY_SFC_SW_DWN_2015_a.parquet"
    )
    good = pd.DataFrame({"grid": ["ceres1deg"], "lgd_district_code": [509], "lon": [80.5],
                         "lat": [17.5], "weight": [1.0]})
    out = build_daily(tmp_path, good, ("ALLSKY_SFC_SW_DWN",), range(2015, 2016))
    assert out["ALLSKY_SFC_SW_DWN"].tolist() == [20.0]
    wrong = good.assign(lon=80.625, lat=17.5)  # a MERRA-2 centre
    with pytest.raises(ValueError, match="no data"):
        build_daily(tmp_path, wrong, ("ALLSKY_SFC_SW_DWN",), range(2015, 2016))


def test_ndvi_uses_only_months_published_before_the_cutoff() -> None:
    """A monthly composite enters only if month end + 15 days < cutoff; poisoning every later
    month must not change the features."""
    from krishios_ml.yield_features.modis import ndvi_features

    months = pd.date_range("2015-01-01", "2015-12-01", freq="MS")
    monthly = pd.DataFrame({"lgd_district_code": 509, "month_start": months,
                            "ndvi": np.linspace(0.2, 0.8, len(months))})
    keys = pd.DataFrame({"lgd_district_code": [509], "crop_year": [2015], "season": ["Kharif"],
                         "lead_days": [30], "window_start": [pd.Timestamp("2015-04-02")],
                         "cutoff": [pd.Timestamp("2015-07-01")]})
    a = ndvi_features(monthly, keys)
    # April (published 15 May) and May (published 15 Jun) qualify; June (15 Jul) does not.
    assert a.loc[0, "ndvi_months"] == 2
    assert a.loc[0, "ndvi_last_month_end"] == pd.Timestamp("2015-05-31")
    poisoned = monthly.copy()
    poisoned.loc[poisoned["month_start"] >= "2015-06-01", "ndvi"] = 9.9
    assert a.equals(ndvi_features(poisoned, keys))
    assert a.loc[0, "ndvi_mean"] == pytest.approx(monthly["ndvi"].iloc[3:5].mean())
    scored = ndvi_features(monthly.assign(good_share=0.5), keys)
    assert scored.loc[0, "ndvi_good_share"] == pytest.approx(0.5)


def test_ndvi_anomaly_normals_come_from_training_rows_only() -> None:
    from krishios_ml.yield_.data import NDVI, add_ndvi

    frame = pd.DataFrame({"lgd_district_code": 509, "crop_year": [2010, 2011, 2017],
                          "season": "Kharif", "lead_days": 0,
                          "split": ["train", "train", "val"]})
    ndvi = frame.drop(columns="split").assign(**{c: 0.0 for c in NDVI})
    ndvi["ndvi_last"] = [0.4, 0.6, 0.9]
    z = add_ndvi(frame, ndvi)["ndvi_last_z"].to_numpy()
    sd = np.std([0.4, 0.6], ddof=1)
    assert z[2] == pytest.approx((0.9 - 0.5) / sd)
    changed = ndvi.assign(ndvi_last=[0.4, 0.6, 50.0])
    assert add_ndvi(frame, changed)["ndvi_last_z"].iloc[0] == pytest.approx(z[0])


def test_ndvi_district_mean_masks_bad_pixels_and_scales() -> None:
    from krishios_ml.yield_features.modis import aggregate_month

    ndvi = np.array([[5000, 7000], [-3000, 9000]], dtype="float32")  # raw (scale 1e-4)
    rel = np.array([[0, 1], [0, 3]])  # 3 = cloudy -> masked
    index = np.array([[7, 7], [7, 7]])
    out = aggregate_month(ndvi, rel, index, nodata=-3000)
    assert abs(out.loc[0, "ndvi"] - 0.6) < 1e-6 and out.loc[0, "good_share"] == 0.5
