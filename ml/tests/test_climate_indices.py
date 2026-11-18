"""Large-scale climate indices: parsing and what a forecast may see."""

import numpy as np
import pandas as pd
import pytest

from krishios_ml.yield_features import climate


def test_parsers_read_values_and_drop_missing_marks() -> None:
    psl = " 2015 2016\n2015 " + " ".join(["0.5"] * 11 + ["-99.99"]) + "\nfooter text\n"
    t = climate.parse_year_table(psl, "soi")
    assert len(t) == 11 and t["value"].iloc[0] == 0.5
    sst = ("YR MON NINO1+2 ANOM NINO3 ANOM NINO4 ANOM NINO3.4 ANOM\n"
           "2015 2 1 2 3 4 5 6 27.0 0.7\n")
    s = climate.parse_sstoi(sst)
    assert s["value"].tolist() == [0.7] and s["month_start"][0] == pd.Timestamp(2015, 2, 1)


def test_olr_reads_only_the_standardized_section() -> None:
    row = "2015" + "".join(f"{v:6.1f}" for v in [1.0] * 11) + "-999.9"
    other = "2015" + "".join(f"{v:6.1f}" for v in [9.0] * 12)
    t = climate.parse_olr(f"ORIGINAL DATA\n{other}\nSTANDARDIZED DATA\n{row}\n")
    assert len(t) == 11 and set(t["value"]) == {1.0}


DODS = """Dataset { } x;
---------------------------------------------
air.air[2][2][2]
[0][0], 1.0, 3.0
[0][1], 5.0, 7.0
[1][0], 2.0, 4.0
[1][1], 6.0, 8.0

air.time[2]
10.0, 41.0

air.lat[2]
0.0, 60.0
"""


def test_gridded_response_is_parsed_and_area_weighted() -> None:
    grid = climate.parse_dods_grid(DODS, "air")
    assert grid.shape == (2, 2, 2) and grid[1, 1, 0] == 6.0
    assert climate.parse_dods_vector(DODS, "lat").tolist() == [0.0, 60.0]
    mean = climate.box_mean(grid, np.array([0.0, 60.0]))
    assert mean[0] == pytest.approx((1 * 1 + 3 * 1 + 5 * 0.5 + 7 * 0.5) / 3)
    grid[0, 0, 0] = -9e36  # missing cells are ignored
    assert climate.box_mean(grid, np.array([0.0, 60.0]), -9e36)[0] == pytest.approx(
        (3 * 1 + 5 * 0.5 + 7 * 0.5) / 2)


def drivers():
    months = pd.date_range("2000-01-01", "2015-12-01", freq="MS")
    d = pd.DataFrame({"driver": "rain_nepal", "month_start": months,
                      "value": (months.year - 1990 + months.month / 12).astype(float)})
    return climate.standardize(d)


def test_driver_anomalies_use_only_baseline_years_and_respect_the_lag() -> None:
    d = drivers()
    changed = d.drop(columns="z").copy()
    changed.loc[changed["month_start"].dt.year >= 2010, "value"] = 500.0
    z = climate.standardize(changed)
    assert z.loc[z["month_start"] == "2005-01-01", "z"].iloc[0] == pytest.approx(
        d.loc[d["month_start"] == "2005-01-01", "z"].iloc[0])
    # rain_nepal has a 90-day lag: at 1 Jun 2015 the newest usable month is February.
    r = climate.driver_features(d, pd.Series([pd.Timestamp("2015-06-01")])).iloc[0]
    feb = d.loc[d["month_start"] == "2015-02-01", "z"].iloc[0]
    assert r["drv_rain_nepal_last"] == pytest.approx(feb)


def test_regional_drivers_are_blank_outside_their_states() -> None:
    df = pd.DataFrame({"lgd_state_code": [9, 3], **dict.fromkeys(climate.DRIVER_FEATURES, 0.5)})
    df["drv_rain_nepal_last"] = 1.0
    out = climate.route_drivers(df)
    assert out["drv_rain_nepal_last"].iloc[0] == 1.0
    assert np.isnan(out["drv_rain_nepal_last"].iloc[1])  # Punjab
    assert np.isnan(out["drv_u200_central_asia_last"].iloc[0])  # Uttar Pradesh
    assert out["drv_u200_central_asia_last"].iloc[1] == 0.5
    assert out["drv_sst_arabian_sea_last"].notna().all()


def table(values, start="2015-01-01"):
    months = pd.date_range(start, periods=len(values), freq="MS")
    return pd.DataFrame({"index": "dmi", "month_start": months, "value": values})


def test_only_published_months_are_used() -> None:
    t = table([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    # At 1 Jun: April ended 30 Apr, and 30 Apr + 30 days = 30 May is before the cutoff. May is not.
    r = climate.features_at(t, pd.Series([pd.Timestamp("2015-06-01")])).iloc[0]
    assert r["clim_dmi_last"] == 4.0
    assert r["clim_dmi_mean3"] == pytest.approx(3.0)
    assert r["clim_dmi_change3"] == pytest.approx(3.0)
    assert np.isnan(r["clim_soi_last"])


def test_future_months_cannot_change_features() -> None:
    t = table([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    cut = pd.Series([pd.Timestamp("2015-06-01")])
    a = climate.features_at(t, cut)
    poisoned = t.copy()
    poisoned.loc[poisoned["month_start"] >= "2015-05-01", "value"] = 999.0
    pd.testing.assert_frame_equal(a, climate.features_at(poisoned, cut))
