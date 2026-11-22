"""Phase 10d seasonal outlook core: scores, terciles, trend handling, no look-ahead."""

import numpy as np
import pandas as pd
import pytest

from krishios_ml.seasonal.outlook import (
    Config,
    category,
    detrended,
    hindcast_year,
    rps,
    terciles_of,
)


def test_rps_hand_values() -> None:
    perfect = rps(np.array([[0.0, 0.0, 1.0]]), np.array([2]))
    worst = rps(np.array([[1.0, 0.0, 0.0]]), np.array([2]))
    clim = rps(np.array([[1 / 3, 1 / 3, 1 / 3]]), np.array([2]))
    assert perfect[0] == 0 and worst[0] == pytest.approx(1.0)
    assert clim[0] == pytest.approx(((1 / 3) ** 2 + (2 / 3) ** 2) / 2)


def test_terciles_split_history_into_thirds() -> None:
    hist = np.arange(30, dtype=float).reshape(1, 30)
    cat_h, cat_t = terciles_of(hist, np.array([29.0]))
    assert [int((cat_h == c).sum()) for c in range(3)] == [10, 10, 10]
    assert cat_t[0] == 2


def test_detrending_removes_a_linear_trend() -> None:
    years = np.arange(1951, 1991)
    hist = (0.05 * (years - 1951) + 30).reshape(1, -1)
    h, t = detrended(hist, np.array([0.05 * (1991 - 1951) + 30]), years, 1991)
    assert np.allclose(h, 0) and t[0] == pytest.approx(0, abs=1e-9)


def test_category_thresholds_and_missing() -> None:
    assert category(0.7, 0.5) == 1 and category(-0.5, 0.5) == -1 and category(0.2, 0.5) == 0
    assert category(float("nan"), 0.5) == 0


def test_target_year_never_informs_its_own_forecast() -> None:
    years = list(range(1951, 1991))
    rng = np.random.default_rng(0)
    values = pd.DataFrame(rng.normal(size=(3, len(years))), index=[1, 2, 3], columns=years)
    states = pd.DataFrame({"enso": 0, "iod": 0}, index=years)
    base = hindcast_year(values, states, np.array(["a", "a", "b"]), 1990, Config(lam=0))
    values[1990] = 1e6  # an extreme target value must not change the probabilities
    again = hindcast_year(values, states, np.array(["a", "a", "b"]), 1990, Config(lam=0))
    cols = ["p_below", "p_near", "p_above"]
    assert np.allclose(base[cols], again[cols]) and (again["obs"] == 2).all()
    assert hindcast_year(values, states, np.array(["a", "a", "b"]), 1975, Config()) is None
