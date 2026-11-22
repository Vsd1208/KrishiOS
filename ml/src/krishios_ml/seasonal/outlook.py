"""Phase 10d: district tercile outlook from El Nino / IOD analog years (hindcast core).

For a target season and year, only information available before the issue date is used:

- history = all years before the target year (an expanding window, as a forecaster would have);
- terciles per district from the history (optionally of residuals from a linear trend fitted on
  the history, for temperature, which is warming);
- analog years = history years in the same ENSO state (ONI) and, if asked and there are enough,
  the same IOD state (DMI), read ``LAG_MONTHS`` before the issue month;
- district probabilities = analog tercile counts shrunk toward 1/3 each (prior strength ``k``),
  then toward the state's mean probabilities (weight ``lam``).

Scores: ranked probability score (RPS) against climatology (1/3 each) -> RPSS.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

ISSUE_MONTH = {"JJAS": 6, "OND": 10, "JF": 1, "MAM": 3}
LAG_MONTHS = 2  # index value used: two months before the issue month (surely published)
ENSO_T, IOD_T = 0.5, 0.4
MIN_ANALOGS = 6


@dataclass(frozen=True, slots=True)
class Config:
    k: float = 6.0  # prior strength toward 1/3 each, in pseudo-years
    lam: float = 0.5  # weight of the state mean
    detrend: bool = False  # terciles of residuals from a linear trend on the history
    use_iod: bool = False
    # Phase 10d revision: "analog" (ENSO/IOD analog years), "ocn" (optimal climate normals:
    # category frequencies of the last ``n_recent`` years, which carries trends such as
    # warming), or "blend" (mean of the two).
    method: str = "analog"
    n_recent: int = 10


def category(value: float, threshold: float) -> int:
    """-1 / 0 / +1 (e.g. La Nina / neutral / El Nino); 0 when the value is unknown."""
    if np.isnan(value):
        return 0
    return 1 if value >= threshold else (-1 if value <= -threshold else 0)


def predictor_states(indices: pd.DataFrame, season: str, years: range) -> pd.DataFrame:
    """ENSO and IOD state for each target year, read LAG_MONTHS before the issue month."""
    piv = indices.pivot_table(index="month_start", columns="index", values="value")
    rows = []
    for y in years:
        issue = pd.Timestamp(y, ISSUE_MONTH[season], 1)
        at = issue - pd.DateOffset(months=LAG_MONTHS)
        oni = float(piv["oni"].get(at, np.nan)) if "oni" in piv else np.nan
        dmi = float(piv["dmi"].get(at, np.nan)) if "dmi" in piv else np.nan
        rows.append({"year": y, "enso": category(oni, ENSO_T), "iod": category(dmi, IOD_T),
                     "oni": oni, "dmi": dmi})
    return pd.DataFrame(rows).set_index("year")


def terciles_of(history: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Categories (0 below, 1 near, 2 above) of history (d, n) and target (d,) values, using
    tercile limits computed from the history of each district."""
    lo = np.nanpercentile(history, 100 / 3, axis=1, keepdims=True)
    hi = np.nanpercentile(history, 200 / 3, axis=1, keepdims=True)
    cat_h = np.where(history < lo, 0, np.where(history > hi, 2, 1))
    cat_t = np.where(target < lo[:, 0], 0, np.where(target > hi[:, 0], 2, 1))
    return cat_h, cat_t


def detrended(history: np.ndarray, target: np.ndarray, hyears: np.ndarray,
              tyear: int) -> tuple[np.ndarray, np.ndarray]:
    """Residuals from a per-district least-squares line fitted on the history only."""
    x = hyears - hyears.mean()
    xm = (tyear - hyears.mean())
    ym = np.nanmean(history, axis=1, keepdims=True)
    slope = np.nansum(x * (history - ym), axis=1, keepdims=True) / np.sum(x * x)
    return history - (ym + slope * x), target - (ym[:, 0] + slope[:, 0] * xm)


def rps(prob: np.ndarray, obs: np.ndarray) -> np.ndarray:
    """Ranked probability score per row for 3 ordered categories."""
    onehot = np.eye(3)[obs]
    return np.sum((np.cumsum(prob, axis=1) - np.cumsum(onehot, axis=1)) ** 2, axis=1) / 2


CLIM = np.full(3, 1 / 3)


def hindcast_year(values: pd.DataFrame, states: pd.DataFrame, regions: np.ndarray,
                  tyear: int, cfg: Config) -> pd.DataFrame | None:
    """Probabilities and observed category for every district in one target year.

    ``values``: districts x years (one variable, one season). ``regions``: state per district.
    """
    hyears = np.array([y for y in values.columns if y < tyear])
    if tyear not in values.columns or len(hyears) < 30:
        return None
    hist = values[hyears].to_numpy(dtype="float64")
    targ = values[tyear].to_numpy(dtype="float64")
    if cfg.detrend:
        hist, targ = detrended(hist, targ, hyears, tyear)
    cat_h, cat_t = terciles_of(hist, targ)
    st = states.loc[tyear]
    same = states.loc[hyears, "enso"].to_numpy() == st["enso"]
    if cfg.use_iod:
        both = same & (states.loc[hyears, "iod"].to_numpy() == st["iod"])
        if both.sum() >= MIN_ANALOGS:
            same = both

    def shrunk(mask: np.ndarray) -> np.ndarray:
        a = cat_h[:, mask]
        valid = ~np.isnan(hist[:, mask])
        counts = np.stack([((a == c) & valid).sum(axis=1) for c in range(3)], axis=1)
        return (counts + cfg.k / 3) / (valid.sum(axis=1, keepdims=True) + cfg.k)

    recent = hyears >= hyears.max() - cfg.n_recent + 1
    if cfg.method == "ocn":
        p_d = shrunk(recent)
    elif cfg.method == "blend":
        p_d = (shrunk(same) + shrunk(recent)) / 2
    else:
        p_d = shrunk(same)
    p_r = pd.DataFrame(p_d).groupby(regions).transform("mean").to_numpy()
    p = (1 - cfg.lam) * p_d + cfg.lam * p_r
    ok = ~np.isnan(targ)
    out = pd.DataFrame(p[ok], columns=["p_below", "p_near", "p_above"])
    out["district"] = values.index.to_numpy()[ok]
    out["obs"] = cat_t[ok]
    out["n_analogs"] = int(same.sum())
    out["year"] = tyear
    return out


def score(frame: pd.DataFrame) -> dict:
    p = frame[["p_below", "p_near", "p_above"]].to_numpy()
    obs = frame["obs"].to_numpy()
    r = rps(p, obs).mean()
    r_clim = rps(np.tile(CLIM, (len(obs), 1)), obs).mean()
    return {"n": len(obs), "rps": round(float(r), 5), "rps_clim": round(float(r_clim), 5),
            "rpss": round(float(1 - r / r_clim), 4)}


def reliability(frame: pd.DataFrame, column: str = "p_above", category_index: int = 2,
                bins: tuple[float, ...] = (0, 0.25, 0.3, 0.35, 0.4, 0.5, 1.0)) -> list[dict]:
    """Observed frequency of a category against its forecast probability, per bin."""
    hit = (frame["obs"] == category_index).astype(float)
    cut = pd.cut(frame[column], bins=list(bins), include_lowest=True)
    g = pd.DataFrame({"bin": cut, "p": frame[column], "hit": hit}).groupby("bin", observed=True)
    return [{"bin": str(k), "n": len(v), "mean_forecast": round(float(v["p"].mean()), 3),
             "observed": round(float(v["hit"].mean()), 3)} for k, v in g if len(v)]


def outlook_next(values: pd.DataFrame, regions: np.ndarray, cfg: Config) -> pd.DataFrame:
    """Recent-normals ("ocn") outlook for the season after the last year in ``values``.

    Uses every year in ``values`` as history. Returns per district the three probabilities and
    the tercile limits (in the variable's own units) that define below / near / above normal.
    """
    if cfg.method != "ocn":
        raise ValueError("the served outlook uses recent normals only (Phase 10d test)")
    hyears = np.array(sorted(values.columns))
    hist = values[hyears].to_numpy(dtype="float64")
    lo = np.nanpercentile(hist, 100 / 3, axis=1)
    hi = np.nanpercentile(hist, 200 / 3, axis=1)
    cat = np.where(hist < lo[:, None], 0, np.where(hist > hi[:, None], 2, 1))
    recent = hyears >= hyears.max() - cfg.n_recent + 1
    valid = ~np.isnan(hist[:, recent])
    counts = np.stack([((cat[:, recent] == c) & valid).sum(axis=1) for c in range(3)], axis=1)
    p = (counts + cfg.k / 3) / (valid.sum(axis=1, keepdims=True) + cfg.k)
    if cfg.lam:
        p = (1 - cfg.lam) * p + cfg.lam * pd.DataFrame(p).groupby(regions).transform(
            "mean").to_numpy()
    out = pd.DataFrame(p, columns=["p_below", "p_near", "p_above"])
    out["district"] = values.index.to_numpy()
    out["lower_tercile"], out["upper_tercile"] = lo, hi
    out["history_from"], out["history_to"] = int(hyears.min()), int(hyears.max())
    return out
