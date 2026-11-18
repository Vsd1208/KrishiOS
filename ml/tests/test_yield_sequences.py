"""B5 inputs: the dekad timeline and what a forecast is allowed to see."""

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")

from krishios_ml.yield_.model import ModelConfig, YieldModel, assemble  # noqa: E402
from krishios_ml.yield_.sequences import DEKADS, NOT_AVAILABLE, WEATHER_COLS, build  # noqa: E402


def stats() -> dict:
    return {"w_mu": torch.zeros(5), "w_sd": torch.ones(5),
            "n_mu": torch.zeros(2), "n_sd": torch.ones(2)}


def view(weather, ndvi, pub, lead):
    return assemble(torch.as_tensor(weather), torch.as_tensor(ndvi),
                    torch.as_tensor(pub), torch.tensor([lead]), stats())


def records():
    weather = np.ones((1, DEKADS, 5), dtype="float32")
    ndvi = np.full((1, DEKADS, 2), np.nan, dtype="float32")
    pub = np.full((1, DEKADS), NOT_AVAILABLE, dtype="int16")
    ndvi[0, 3], pub[0, 3] = (0.5, 0.9), 49   # visible at lead 0 (cutoff day 60)
    ndvi[0, 6], pub[0, 6] = (0.6, 0.9), 75   # needs lead 30
    return weather, ndvi, pub


def test_lead_zero_shows_only_finished_dekads_and_published_ndvi() -> None:
    x = view(*records(), 0)[0]
    assert x[:, 7].tolist() == [1.0] * 6 + [0.0] * 9
    assert x[:, 8].nonzero().flatten().tolist() == [3]
    assert x[3, 5] == pytest.approx(0.5) and x[6, 5] == 0
    later = view(*records(), 30)[0]
    assert later[:, 7].sum() == 9 and later[:, 8].nonzero().flatten().tolist() == [3, 6]


def test_changing_future_values_cannot_change_the_view() -> None:
    weather, ndvi, pub = records()
    a = view(weather, ndvi, pub, 0)
    weather[:, 6:] = 999.0
    ndvi[0, 6] = 999.0
    assert torch.equal(a, view(weather, ndvi, pub, 0))


def test_ndvi_published_on_the_cutoff_day_is_hidden() -> None:
    weather, ndvi, pub = records()
    pub[0, 3] = 60
    assert view(weather, ndvi, pub, 0)[0, :, 8].sum() == 0


def test_build_places_weather_and_ndvi_by_date(tmp_path) -> None:
    days = pd.date_range("2015-01-01", "2015-12-31")
    daily = pd.DataFrame({"lgd_district_code": 509, "date": days,
                          **{c: 1.0 for c in WEATHER_COLS}}).astype({c: "float32"
                                                                     for c in WEATHER_COLS})
    daily.to_parquet(tmp_path / "2015.parquet")
    monthly = pd.DataFrame({"lgd_district_code": 509,
                            "month_start": pd.to_datetime(["2015-04-01", "2015-05-01"]),
                            "ndvi": [0.4, 0.5], "good_share": [1.0, 0.8]})
    keys = pd.DataFrame({"lgd_district_code": [509], "crop_year": [2015], "season": ["Kharif"]})
    r = build(keys, tmp_path, monthly)
    assert r["weather"][0, 0, 0] == pytest.approx(10.0)  # 10 days of 1 mm
    assert r["weather"][0, 0, 1] == pytest.approx(1.0)
    # Window starts 2 Apr: 30 Apr is day 28 (dekad 2), published day 43; 31 May is day 59.
    assert r["ndvi"][0, 2, 0] == pytest.approx(0.4) and r["ndvi_pub"][0, 2] == 43
    assert r["ndvi"][0, 5, 1] == pytest.approx(0.8) and r["ndvi_pub"][0, 5] == 74


def test_model_output_shape() -> None:
    cfg = ModelConfig(n_static=4, n_crops=3, n_seasons=2, n_states=2, hidden=8)
    m = YieldModel(cfg)
    x = view(*records(), 30).repeat(2, 1, 1)
    i = torch.zeros(2, dtype=torch.long)
    assert m(x, torch.zeros(2, 4), i, i, i, i).shape == (2,)
