"""Modelling frames for the yield baselines (Phase 8).

Target: every model predicts the **ratio** of the yield to the series' own historical mean
(``r = yield / hist_mean``); the forecast is ``hist_mean * r_hat``. History uses only years
``<= Y - HISTORY_LAG``: APY district statistics are published with a delay, so last year's
yield is not known when this year's forecast is made.

Evaluation set (shared by every baseline, so comparisons are like for like): rows with at
least ``MIN_HISTORY`` prior years, a positive historical mean, and weather features.

**Primary metrics** use ``eval_clean`` rows: ``eval_ok`` minus implausibly high labels
(flagged by the Phase 6 robust outlier check *and* above the series' history, or more than
``MAX_RATIO`` times the history), which are almost always unit or entry errors. Low-side
outliers (crop failures, zero yields) are real and stay in. The rule uses labels only and was
fixed before any model was scored. Secondary metrics use all ``eval_ok`` rows.

Weather normals (district x season x lead means/stds) are fitted on the train split only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

HISTORY_LAG = 2
MIN_HISTORY = 3
SERIES = ["lgd_district_code", "crop_canonical", "season"]
KEYS = ["lgd_district_code", "crop_year", "season"]
WEATHER = ["rain_sum", "rain_days", "max_dry_spell", "tmax_mean", "tmin_mean", "heat_days",
           "gdd", "rh_mean", "srad_mean"]
HISTORY = ["hist_trend_ratio", "hist_last_ratio", "hist_cv", "hist_n", "log_hist_mean"]
CATEGORICAL = ["crop_canonical", "season", "lgd_state_code"]
TARGET_CLIP = (0.0, 3.0)
MAX_RATIO = 10.0  # training targets only; evaluation uses the raw yields


def _series_history(years: np.ndarray, ys: np.ndarray, lag: int) -> np.ndarray:
    """For each row, stats of the rows with year <= own year - lag. Returns (n, 5)."""
    out = np.full((len(years), 5), np.nan)
    for i, y in enumerate(years):
        m = years <= y - lag
        n = int(m.sum())
        if n == 0:
            out[i, 3] = 0
            continue
        hy, hv = years[m], ys[m]
        mean = hv.mean()
        trend = mean
        if n >= 5 and np.ptp(hy) > 0:
            slope, icpt = np.polyfit(hy, hv, 1)
            trend = slope * y + icpt
        last = hv[np.argmax(hy)]
        out[i] = (mean, trend, last, n, hv.std() / mean if mean > 0 else np.nan)
    return out


def history_features(labels: pd.DataFrame, lag: int = HISTORY_LAG) -> pd.DataFrame:
    df = labels.sort_values([*SERIES, "crop_year"]).reset_index(drop=True)
    parts = []
    for _, g in df.groupby(SERIES, sort=False):
        parts.append(_series_history(g["crop_year"].to_numpy(), g["yield"].to_numpy(), lag))
    h = np.vstack(parts)
    df["hist_mean"], df["hist_n"] = h[:, 0], h[:, 3]
    with np.errstate(divide="ignore", invalid="ignore"):
        df["hist_trend_ratio"] = h[:, 1] / h[:, 0]
        df["hist_last_ratio"] = h[:, 2] / h[:, 0]
        df["log_hist_mean"] = np.log(h[:, 0])
    df["hist_cv"] = h[:, 4]
    df["hist_last"] = h[:, 2]
    return df


def weather_normals(frame: pd.DataFrame) -> pd.DataFrame:
    """District x season x lead mean/std of each weather feature, from the rows passed in
    (call it with train rows only)."""
    g = frame.drop_duplicates([*KEYS, "lead_days"]).groupby(
        ["lgd_district_code", "season", "lead_days"])[WEATHER]
    mean, std = g.mean().add_suffix("_mu"), g.std().add_suffix("_sd")
    return mean.join(std).reset_index()


def add_anomalies(frame: pd.DataFrame, normals: pd.DataFrame) -> pd.DataFrame:
    out = frame.merge(normals, on=["lgd_district_code", "season", "lead_days"], how="left")
    for c in WEATHER:
        sd = out[f"{c}_sd"].where(out[f"{c}_sd"] > 0)
        out[f"{c}_z"] = (out[c] - out[f"{c}_mu"]) / sd
    return out.drop(columns=[f"{c}_{s}" for c in WEATHER for s in ("mu", "sd")])


def build_frame(labels: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """All leads; one row per label x lead, with history, target ratio and eval flag."""
    h = history_features(labels)
    f = features[features["has_weather"].fillna(False).astype(bool)]
    df = h.merge(f[[*KEYS, "lead_days", *WEATHER]], on=KEYS, how="inner")
    df["ratio"] = df["yield"] / df["hist_mean"]
    df["eval_ok"] = (df["hist_n"] >= MIN_HISTORY) & (df["hist_mean"] > 0)
    implausible = (df["outlier_flag"] & (df["ratio"] > 1)) | (df["ratio"] > MAX_RATIO)
    df["eval_clean"] = df["eval_ok"] & ~implausible
    df["lgd_state_code"] = df["lgd_state_code"].astype(int)
    return df


WEATHER_Z = [f"{c}_z" for c in WEATHER]


def feature_sets() -> dict[str, list[str]]:
    return {
        "full": [*HISTORY, *WEATHER, *WEATHER_Z, *CATEGORICAL],
        "weather_only": [*WEATHER, *WEATHER_Z, *CATEGORICAL],
        "history_only": [*HISTORY, *CATEGORICAL],
    }
