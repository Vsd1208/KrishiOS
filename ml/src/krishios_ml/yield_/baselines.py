"""Yield baselines B1-B4 and the per-crop LightGBM reference (Phase 8).

Every model predicts the ratio ``r = yield / hist_mean`` (see ``data.py``).

- **B1 hist_mean:** r = 1 (the series' own historical mean). **B1p persistence:** the last
  available yield (year <= Y-2).
- **B2 ridge:** linear model on history, weather and weather-anomaly features plus one-hot
  crop / season / state.
- **B3 lgbm:** one multi-crop LightGBM on the same features (crop, season, state categorical).
- **B4 lgbm_weather:** single modality, weather only (no yield history). Vegetation and soil
  single-modality models wait for NDVI / soil data.
- **per_crop_lgbm:** one LightGBM per crop (RQ5 reference for the shared model).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from krishios_ml.yield_.data import CATEGORICAL, TARGET_CLIP


def _target(df: pd.DataFrame) -> np.ndarray:
    return df["ratio"].clip(*TARGET_CLIP).to_numpy()


class HistMean:
    name = "B1_hist_mean"

    def fit(self, train, val):
        return self

    def predict(self, df):
        return np.ones(len(df))


class Persistence:
    name = "B1p_persistence"

    def fit(self, train, val):
        return self

    def predict(self, df):
        return df["hist_last_ratio"].fillna(1.0).to_numpy()


@dataclass
class RidgeModel:
    features: list[str]
    alpha: float = 1.0
    name: str = "B2_ridge"
    _pipe: object = None

    def fit(self, train, val):
        from sklearn.compose import ColumnTransformer
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler

        num = [c for c in self.features if c not in CATEGORICAL]
        cat = [c for c in self.features if c in CATEGORICAL]
        pre = ColumnTransformer([
            ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), num),
            ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=20), cat),
        ])
        self._pipe = make_pipeline(pre, Ridge(alpha=self.alpha))
        x = train[self.features].replace([np.inf, -np.inf], np.nan)
        self._pipe.fit(x, _target(train))
        return self

    def predict(self, df):
        x = df[self.features].replace([np.inf, -np.inf], np.nan)
        return np.clip(self._pipe.predict(x), 0, None)


@dataclass
class LGBMModel:
    features: list[str]
    params: dict = field(default_factory=dict)
    seed: int = 0
    name: str = "B3_lgbm"
    _model: object = None
    _cats: dict = field(default_factory=dict)
    best_iteration: int | None = None

    def _params(self) -> dict:
        return {"objective": "huber", "alpha": 0.5, "learning_rate": 0.05, "num_leaves": 63,
                "min_child_samples": 100, "feature_fraction": 0.8, "bagging_fraction": 0.8,
                "bagging_freq": 1, "lambda_l2": 1.0, "verbose": -1, "seed": self.seed,
                "num_threads": 0, **self.params}

    def _x(self, df):
        x = df[self.features].replace([np.inf, -np.inf], np.nan).copy()
        for c in self.features:
            if c in CATEGORICAL:
                x[c] = pd.Categorical(x[c], categories=self._cats[c])
        return x

    def fit(self, train, val):
        import lightgbm as lgb

        self._cats = {c: sorted(train[c].unique()) for c in self.features if c in CATEGORICAL}
        p = self._params()
        dtrain = lgb.Dataset(self._x(train), _target(train))
        dval = lgb.Dataset(self._x(val), _target(val), reference=dtrain)
        self._model = lgb.train(p, dtrain, num_boost_round=3000, valid_sets=[dval],
                                callbacks=[lgb.early_stopping(100, verbose=False)])
        self.best_iteration = self._model.best_iteration
        return self

    def predict(self, df):
        return np.clip(self._model.predict(self._x(df), num_iteration=self.best_iteration),
                       0, None)

    def fit_full(self, df, rounds: int):
        """Serving refit on every labelled row with the validated number of rounds (no early
        stopping: there is no held-out data left to stop on)."""
        import lightgbm as lgb

        self._cats = {c: sorted(df[c].unique()) for c in self.features if c in CATEGORICAL}
        p = self._params()
        self._model = lgb.train(p, lgb.Dataset(self._x(df), _target(df)),
                                num_boost_round=rounds)
        self.best_iteration = rounds
        return self


@dataclass
class PerCropLGBM:
    """One LightGBM per crop; crops with fewer than ``min_train`` train rows get no model
    (their rows fall back to B1 and are reported as such)."""

    features: list[str]
    params: dict = field(default_factory=dict)
    seed: int = 0
    min_train: int = 200
    name: str = "per_crop_lgbm"
    models: dict = field(default_factory=dict)

    def fit(self, train, val):
        feats = [f for f in self.features if f != "crop_canonical"]
        for crop, tr in train.groupby("crop_canonical"):
            va = val[val["crop_canonical"] == crop]
            if len(tr) < self.min_train or len(va) < 20:
                continue
            m = LGBMModel(feats, {"min_child_samples": 30, **self.params}, self.seed,
                          name=f"per_crop:{crop}")
            self.models[crop] = m.fit(tr, va)
        return self

    def predict(self, df):
        out = np.ones(len(df))
        for crop, idx in df.groupby("crop_canonical").indices.items():
            if crop in self.models:
                out[idx] = self.models[crop].predict(df.iloc[idx])
        return out


# --- evaluation -------------------------------------------------------------------------------

def _metrics(y: np.ndarray, yhat: np.ndarray) -> dict[str, float]:
    err = yhat - y
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return {"mae": float(np.abs(err).mean()), "rmse": float(np.sqrt((err ** 2).mean())),
            "r2": float(1 - (err ** 2).sum() / ss_tot) if ss_tot > 0 else float("nan")}


def per_crop(df: pd.DataFrame, pred_yield: np.ndarray) -> pd.DataFrame:
    d = df.assign(_p=pred_yield)
    rows = []
    for crop, g in d.groupby("crop_canonical"):
        y, p = g["yield"].to_numpy(), g["_p"].to_numpy()
        m = _metrics(y, p)
        mean = float(y.mean())
        rows.append({"crop": crop, "tier": g["tier"].mode().iloc[0],
                     "unit": g["yield_unit"].iloc[0], "n": len(g), "mean_yield": mean, **m,
                     "nmae": m["mae"] / mean if mean > 0 else float("nan")})
    return pd.DataFrame(rows)


def summarise(table: pd.DataFrame, tiers=("A",)) -> dict[str, float]:
    t = table[table["tier"].isin(tiers)]
    return {"crops": len(t), "nmae_median": float(t["nmae"].median()),
            "nmae_worst_decile": float(t["nmae"].quantile(0.9)),
            "r2_median": float(t["r2"].median())}


def conformal_q(val: pd.DataFrame, pred_ratio: np.ndarray, coverage: float = 0.8,
                by: str = "tier") -> dict[str, float]:
    """Split-conformal half-width in ratio space, per group, from validation residuals."""
    res = np.abs(val["ratio"].to_numpy() - pred_ratio)
    out = {}
    for k, idx in val.groupby(by).indices.items():
        r = np.sort(res[idx])
        n = len(r)
        rank = min(n - 1, int(np.ceil((n + 1) * coverage)) - 1)
        out[str(k)] = float(r[rank])
    return out


def interval_coverage(df: pd.DataFrame, pred_ratio: np.ndarray, q: dict[str, float],
                      by: str = "tier") -> dict[str, float]:
    half = df[by].astype(str).map(q).to_numpy()
    lo = np.clip(pred_ratio - half, 0, None) * df["hist_mean"].to_numpy()
    hi = (pred_ratio + half) * df["hist_mean"].to_numpy()
    y = df["yield"].to_numpy()
    inside = (y >= lo) & (y <= hi)
    return {str(k): float(inside[idx].mean())
            for k, idx in df.groupby(by).indices.items()}
