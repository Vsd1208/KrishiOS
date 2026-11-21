"""Phase 10 RQ4 and RQ5: held-out states, held-out years and unseen crops (validation only).

Studies (``--study``), each for B3 (LightGBM, the served model) or B5 (the shared neural model):

- ``states`` (RQ4): states are split into 5 groups, balanced by rows. For each group the model is
  trained without those states and scored on their 2016-18 rows; a model trained with them is the
  comparison. Both stop early on the 2016-18 rows of the other states only. Pooled over groups,
  every validation row gets an unseen-state and a seen-state forecast.
- ``years`` (RQ4, B3 only): a model trained on years up to 2007 is scored on 2010-12, 2013-15 and
  2016-18 (gaps of 3, 6 and 9 years) against models retrained up to just before each period. Both
  stop early on the two years before their own training end, never on the scored period.
- ``crops`` (RQ5): each tier-A crop is removed from training (k = 0) or kept for only k randomly
  chosen districts (k-shot), and scored on its 2016-18 rows against the model that saw all of it
  and the district historical mean. All three stop early on the other crops' validation rows.
  B5 uses 10 of the 30 crops, chosen before any result: every third crop ordered by districts.

No test split is read. Usage (from ml/)::

    uv run --no-sync python scripts/run_yield_generalisation.py --model b5 --study states
    uv run --no-sync python scripts/run_yield_generalisation.py --model b3 --study crops
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
from run_yield_baselines import FEATURES, LABELS, LEADS, SELECTION, score

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, REPORTS_DIR
from krishios_ml.yield_.baselines import LGBMModel, per_crop
from krishios_ml.yield_.data import add_anomalies, build_frame, feature_sets, weather_normals

SPLIT_ID = "apy-tierv2-ee75501cc5ef"
SEEDS = (0, 1, 2)
N_FOLDS = 5
K_SHOTS = (0, 5)
CROP_LEADS = (0, 60)  # B3 crop study: two leads keep 30 crops x 3 settings x 3 seeds tractable
GAP_PERIODS = ((2010, 2012), (2013, 2015), (2016, 2018))
FROZEN_END = 2009  # the gap model is trained on years up to here (early stopping on 2008-09)


def state_folds(states: pd.Series) -> dict[int, int]:
    """Assign states to folds round-robin by row count (largest first), deterministically."""
    order = states.value_counts().sort_values(ascending=False).index.tolist()
    return {int(s): i % N_FOLDS for i, s in enumerate(order)}


def crop_list(tr: pd.DataFrame, b5: bool) -> list[str]:
    a = tr[tr["tier"] == "A"].groupby("crop_canonical")["lgd_district_code"].nunique()
    crops = sorted(a.index, key=lambda c: (a[c], c))
    return crops[::3] if b5 else crops


def k_shot_mask(tr: pd.DataFrame, crop: str, k: int, seed: int) -> np.ndarray:
    """Training rows to keep: every other crop, plus ``crop`` in k random districts."""
    other = (tr["crop_canonical"] != crop).to_numpy()
    if k == 0:
        return other
    districts = np.sort(tr.loc[~other, "lgd_district_code"].unique())
    chosen = np.random.default_rng(20_000 + seed).permutation(districts)[:k]
    return other | (~other & tr["lgd_district_code"].isin(chosen).to_numpy())


def summary(df: pd.DataFrame, ratio: np.ndarray) -> dict:
    r = score(df.reset_index(drop=True), ratio)
    return {"A_median": r["A"]["nmae_median"], "A_worst_decile": r["A"]["nmae_worst_decile"],
            "B_median": r["B"]["nmae_median"]}


def crop_nmae(df: pd.DataFrame, ratio: np.ndarray) -> float:
    """nMAE of one crop on its clean rows."""
    keep = df["eval_clean"].to_numpy()
    t = per_crop(df[keep], ratio[keep] * df["hist_mean"].to_numpy()[keep])
    return float(t["nmae"].iloc[0]) if len(t) else float("nan")


def stats(values: list[float]) -> dict:
    a = np.asarray(values, dtype=float)
    return {"mean": float(np.nanmean(a)), "sd": float(np.nanstd(a, ddof=1)) if len(a) > 1 else 0.0}


# ---------------------------------------------------------------- resumable progress

class Cache:
    """Finished units (a seed, a lead, a crop) saved as they complete, so an interrupted study
    resumes. Saved units are reused only when the study's config is the same."""

    def __init__(self, path: Path | None, config: dict) -> None:
        self.path, self.config, self.units = path, json.loads(json.dumps(config)), {}
        if path and path.exists():
            saved = json.loads(path.read_text(encoding="utf-8"))
            if saved.get("config") == self.config:
                self.units = saved["units"]
                print(f"resuming: {len(self.units)} units already done", flush=True)

    def get(self, key: str):
        return self.units.get(key)

    def put(self, key: str, value):
        self.units[key] = value
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".part")
            tmp.write_text(json.dumps({"config": self.config, "units": self.units}),
                           encoding="utf-8")
            tmp.replace(self.path)
        return value


CACHE = Cache(None, {})


# ---------------------------------------------------------------- B3 (LightGBM, per lead)

def b3_frames(frame: pd.DataFrame, lead: int, normals_until: int | None = None):
    f = frame[frame["lead_days"] == lead]
    base = f[f["split"] == "train"] if normals_until is None else f[f["crop_year"] <= normals_until]
    return add_anomalies(f, weather_normals(base))


def b3_fit(tr: pd.DataFrame, es: pd.DataFrame, lead: int, seed: int, sel: dict) -> LGBMModel:
    return LGBMModel(feature_sets()["full"], sel[str(lead)]["B3_lgbm"], seed=seed).fit(
        tr.reset_index(drop=True), es.reset_index(drop=True))


def b3_states(frame: pd.DataFrame, sel: dict) -> dict:
    folds = state_folds(frame["lgd_state_code"])
    out: dict = {"seen": [], "unseen": [], "fold_of_state": folds}
    for seed in SEEDS:
        if (unit := CACHE.get(f"states|{seed}")) is not None:
            for name in ("seen", "unseen"):
                out[name].append(unit[name])
            continue
        preds = {"seen": [], "unseen": []}
        rows = []
        for lead in LEADS:
            f = b3_frames(frame, lead)
            tr, va = f[f["split"] == "train"], f[f["split"] == "val"]
            for g in range(N_FOLDS):
                held = [s for s, i in folds.items() if i == g]
                tr_in = tr["lgd_state_code"].astype(int).isin(held)
                va_in = va["lgd_state_code"].astype(int).isin(held)
                es = va[~va_in]
                ev = va[va_in].reset_index(drop=True)
                seen = b3_fit(tr, es, lead, seed, sel)
                unseen = b3_fit(tr[~tr_in], es, lead, seed, sel)
                preds["seen"].append(seen.predict(ev))
                preds["unseen"].append(unseen.predict(ev))
                rows.append(ev)
            print(f"B3 states seed {seed} lead {lead} done", flush=True)
        ev_all = pd.concat(rows, ignore_index=True)
        unit = {}
        for name in ("seen", "unseen"):
            p = np.concatenate(preds[name])
            per_lead = [summary(ev_all[ev_all["lead_days"] == lead],
                                p[(ev_all["lead_days"] == lead).to_numpy()]) for lead in LEADS]
            unit[name] = {k: float(np.mean([r[k] for r in per_lead])) for k in per_lead[0]}
            out[name].append(unit[name])
        CACHE.put(f"states|{seed}", unit)
    return out


def b3_years(frame: pd.DataFrame, sel: dict) -> dict:
    out: dict = {}
    for seed in SEEDS:
        for lead in LEADS:
            if (unit := CACHE.get(f"years|{seed}|{lead}")) is None:
                unit = CACHE.put(f"years|{seed}|{lead}", b3_years_unit(frame, sel, seed, lead))
            for key, v in unit.items():
                out.setdefault(key, {"frozen": [], "fresh": []})
                out[key]["frozen"].append(v["frozen"])
                out[key]["fresh"].append(v["fresh"])
            print(f"B3 years seed {seed} lead {lead} done", flush=True)
    return out


def b3_years_unit(frame: pd.DataFrame, sel: dict, seed: int, lead: int) -> dict:
    """One seed and lead: the model frozen at FROZEN_END against models retrained before each
    period, both scored on that period."""
    unit: dict = {}
    dev = frame[frame["split"].isin(["train", "val"])]
    frozen_f = b3_frames(dev, lead, normals_until=FROZEN_END - 2)
    frozen = b3_fit(frozen_f[frozen_f["crop_year"] <= FROZEN_END - 2],
                    frozen_f[frozen_f["crop_year"].between(FROZEN_END - 1, FROZEN_END)],
                    lead, seed, sel)
    for start, end in GAP_PERIODS:
        fresh_f = b3_frames(dev, lead, normals_until=start - 3)
        fresh = b3_fit(fresh_f[fresh_f["crop_year"] <= start - 3],
                       fresh_f[fresh_f["crop_year"].between(start - 2, start - 1)],
                       lead, seed, sel)
        ev_frozen = frozen_f[frozen_f["crop_year"].between(start, end)]
        ev_fresh = fresh_f[fresh_f["crop_year"].between(start, end)]
        unit[f"{start}-{end}"] = {"frozen": summary(ev_frozen, frozen.predict(ev_frozen)),
                                  "fresh": summary(ev_fresh, fresh.predict(ev_fresh))}
    return unit


def b3_crops(frame: pd.DataFrame, sel: dict) -> dict:
    out: dict = {}
    for lead in CROP_LEADS:
        f = b3_frames(frame, lead)
        tr = f[f["split"] == "train"].reset_index(drop=True)
        va = f[f["split"] == "val"].reset_index(drop=True)
        for crop in crop_list(tr, b5=False):
            if (unit := CACHE.get(f"crops|{lead}|{crop}")) is None:
                is_c = (va["crop_canonical"] == crop).to_numpy()
                ev, es = va[is_c].reset_index(drop=True), va[~is_c]
                unit = {"hist_mean": crop_nmae(ev, np.ones(len(ev))), "seen": [],
                        **{f"k{k}": [] for k in K_SHOTS}}
                for seed in SEEDS:
                    unit["seen"].append(
                        crop_nmae(ev, b3_fit(tr, es, lead, seed, sel).predict(ev)))
                    for k in K_SHOTS:
                        m = b3_fit(tr[k_shot_mask(tr, crop, k, seed)], es, lead, seed, sel)
                        unit[f"k{k}"].append(crop_nmae(ev, m.predict(ev)))
                CACHE.put(f"crops|{lead}|{crop}", unit)
            res = out.setdefault(crop, {"hist_mean": unit["hist_mean"], "seen": [],
                                        **{f"k{k}": [] for k in K_SHOTS}})
            for k in ("seen", *(f"k{k}" for k in K_SHOTS)):
                res[k].extend(unit[k])
            print(f"B3 crops lead {lead} {crop} done", flush=True)
    return out


# ---------------------------------------------------------------- B5 (neural, all leads)

def b5_run(study: str) -> dict:
    import torch
    from run_yield_p1p2 import BEST, Setup, finetune, predict

    class Args:  # the run_yield_b5 defaults
        epochs, patience, batch = 40, 6, 2048

    s = Setup(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    va, tr = s.va_meta.reset_index(drop=True), s.tr_meta.reset_index(drop=True)

    def train(rows_mask: np.ndarray, es_mask: np.ndarray, seed: int) -> np.ndarray:
        rows = torch.tensor(np.nonzero(rows_mask)[0], device=s.device)
        model, info = finetune(s, BEST, seed, Args, rows=rows, es_mask=es_mask)
        pred = predict(model, s)
        print(f"  seed {seed}: best epoch {info['best_epoch']}, {info['seconds']} s", flush=True)
        del model
        torch.cuda.empty_cache()
        return pred

    def by_lead(df: pd.DataFrame, p: np.ndarray) -> dict:
        per = [summary(df[df["lead_days"] == lead], p[(df["lead_days"] == lead).to_numpy()])
               for lead in LEADS]
        return {k: float(np.mean([r[k] for r in per])) for k in per[0]}

    out: dict = {}
    if study == "states":
        folds = state_folds(pd.concat([tr["lgd_state_code"], va["lgd_state_code"]]))
        fold_tr = tr["lgd_state_code"].astype(int).map(folds).to_numpy()
        fold_va = va["lgd_state_code"].astype(int).map(folds).to_numpy()
        out = {"seen": [], "unseen": [], "fold_of_state": folds}
        for seed in SEEDS:
            seen, unseen = np.zeros(len(va)), np.zeros(len(va))
            for g in range(N_FOLDS):
                es, ev = fold_va != g, fold_va == g
                seen[ev] = train(np.ones(len(tr), bool), es, seed)[ev]
                unseen[ev] = train(fold_tr != g, es, seed)[ev]
                print(f"B5 states seed {seed} fold {g} done", flush=True)
            out["seen"].append(by_lead(va, seen))
            out["unseen"].append(by_lead(va, unseen))
    elif study == "crops":
        for crop in crop_list(tr, b5=True):
            is_c = (va["crop_canonical"] == crop).to_numpy()
            ev = va[is_c].reset_index(drop=True)
            res = out.setdefault(crop, {"hist_mean": crop_nmae(ev, np.ones(len(ev))), "seen": [],
                                        **{f"k{k}": [] for k in K_SHOTS}})
            for seed in SEEDS:
                p = train(np.ones(len(tr), bool), ~is_c, seed)
                res["seen"].append(crop_nmae(ev, p[is_c]))
                for k in K_SHOTS:
                    p = train(k_shot_mask(tr, crop, k, seed), ~is_c, seed)
                    res[f"k{k}"].append(crop_nmae(ev, p[is_c]))
            print(f"B5 crops {crop} done", flush=True)
    else:
        raise SystemExit("B5 runs the states and crops studies")
    return out


def summarise(study: str, raw: dict) -> dict:
    if study == "states":
        return {name: {k: stats([r[k] for r in runs]) for k in runs[0]}
                for name, runs in raw.items() if name != "fold_of_state"}
    if study == "years":
        return {period: {name: {k: stats([r[k] for r in runs]) for k in runs[0]}
                         for name, runs in v.items()} for period, v in raw.items()}
    table = {}
    for crop, v in raw.items():
        table[crop] = {"hist_mean": v["hist_mean"],
                       **{k: stats(v[k]) for k in v if k != "hist_mean"}}
    rows = pd.DataFrame({c: {k: (x["mean"] if isinstance(x, dict) else x) for k, x in v.items()}
                         for c, v in table.items()}).T
    overall = {k: float(rows[k].median()) for k in rows.columns}
    beats = {f"{k}_beats_hist_mean": int((rows[k] < rows["hist_mean"]).sum())
             for k in rows.columns if k != "hist_mean"}
    return {"median_over_crops": overall, **beats, "crops": len(rows), "per_crop": table}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=("b3", "b5"), required=True)
    ap.add_argument("--study", choices=("states", "years", "crops"), required=True)
    args = ap.parse_args()
    config = {"phase": "val", "model": args.model, "study": args.study, "seeds": list(SEEDS),
              "folds": N_FOLDS, "k_shots": list(K_SHOTS), "gap_periods": GAP_PERIODS,
              "frozen_end": FROZEN_END,
              "leads": list(CROP_LEADS if args.study == "crops" and args.model == "b3"
                            else LEADS),
              "metric": "tier-A median nMAE (states, years); the crop's own nMAE (crops)"}
    global CACHE
    CACHE = Cache(DATA_DIR / "interim" / f"gen_{args.model}_{args.study}_progress.json", config)
    with track_experiment("yield_generalisation", config, seed=None, split_id=SPLIT_ID) as rec:
        if args.model == "b5":
            raw = b5_run(args.study)
        else:
            labels, feats = pd.read_parquet(LABELS), pd.read_parquet(FEATURES)
            frame = build_frame(labels, feats)
            frame = frame[frame["split"].isin(["train", "val"]) & frame["eval_ok"]]
            del labels, feats
            sel = json.loads(SELECTION.read_text(encoding="utf-8"))["selection"]
            raw = {"states": b3_states, "years": b3_years, "crops": b3_crops}[args.study](
                frame, sel)
        out = summarise(args.study, raw)
        rec.metrics = {k: v for k, v in out.items() if k != "per_crop"}
        path = REPORTS_DIR / "data" / f"yield_gen_{args.model}_{args.study}_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config, "summary": out,
                                    "raw": raw}, indent=1, default=float), encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
    print(json.dumps({k: v for k, v in out.items() if k != "per_crop"}, indent=1, default=float))
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
