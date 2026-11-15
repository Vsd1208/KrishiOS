"""Yield baselines: history uses only years <= Y-2, targets, conformal intervals."""

import numpy as np
import pandas as pd

from krishios_ml.yield_.baselines import conformal_q, interval_coverage, per_crop
from krishios_ml.yield_.data import history_features


def series(years, ys, crop="paddy", district=509):
    return pd.DataFrame({"lgd_district_code": district, "crop_canonical": crop,
                         "season": "Kharif", "crop_year": years, "yield": ys})


def test_history_uses_only_years_at_least_two_before() -> None:
    h = history_features(series([2010, 2011, 2012, 2013, 2014], [1.0, 2.0, 3.0, 4.0, 100.0]))
    row = h[h["crop_year"] == 2014].iloc[0]
    assert row["hist_n"] == 3 and row["hist_mean"] == 2.0  # 2010-2012; not 2013 or 2014
    assert row["hist_last"] == 3.0
    first = h[h["crop_year"] == 2011].iloc[0]
    assert first["hist_n"] == 0 and np.isnan(first["hist_mean"])  # nothing <= 2009


def test_changing_the_current_or_previous_year_does_not_change_history() -> None:
    a = history_features(series([2010, 2011, 2012, 2013, 2014, 2015], [1, 2, 3, 4, 5, 6.0]))
    b = history_features(series([2010, 2011, 2012, 2013, 2014, 2015], [1, 2, 3, 4, 99, 99.0]))
    cols = ["hist_mean", "hist_n", "hist_last", "hist_trend_ratio", "hist_cv"]
    ra, rb = a[a["crop_year"] == 2015], b[b["crop_year"] == 2015]
    assert np.allclose(ra[cols].to_numpy(), rb[cols].to_numpy(), equal_nan=True)


def test_conformal_interval_covers_the_calibration_share() -> None:
    rng = np.random.default_rng(0)
    n = 2000
    val = pd.DataFrame({"ratio": 1 + rng.normal(0, 0.2, n), "tier": "A", "hist_mean": 2.0})
    q = conformal_q(val, np.ones(n), coverage=0.8)
    test = pd.DataFrame({"ratio": 1 + rng.normal(0, 0.2, n), "tier": "A", "hist_mean": 2.0})
    test["yield"] = test["ratio"] * 2.0
    cov = interval_coverage(test, np.ones(n), q)["A"]
    assert 0.77 < cov < 0.83


def test_per_crop_metrics_in_native_units() -> None:
    df = pd.DataFrame({"crop_canonical": ["x"] * 4, "tier": "A", "yield_unit": "t/ha",
                       "yield": [1.0, 2.0, 3.0, 4.0]})
    t = per_crop(df, np.array([1.0, 2.0, 3.0, 5.0]))
    assert t.loc[0, "mae"] == 0.25 and abs(t.loc[0, "nmae"] - 0.1) < 1e-9
