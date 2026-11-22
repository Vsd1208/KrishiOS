"""Phase 10: train B5, the shared multi-crop yield model (validation only).

One model is trained on all four forecast leads. Early stopping and every comparison use the
same validation years and metric as Phase 8 (median nMAE over tier-A crops). The test splits are
dropped before any tensor is built, so this script cannot score them.

Usage (from ml/)::

    uv run --no-sync python scripts/run_yield_b5.py --name b5_all
"""

from __future__ import annotations

import argparse
import itertools
import json
import time

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
import torch
from run_yield_baselines import FEATURES, LABELS, LEADS, mean_std, score
from run_yield_ndvi import MONTHLY, SEASON

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, ML_ROOT, REPORTS_DIR
from krishios_ml.yield_.data import (
    HISTORY,
    KEYS,
    NDVI_Z,
    TARGET_CLIP,
    WEATHER_Z,
    add_anomalies,
    add_ndvi,
    build_frame,
    weather_normals,
)
from krishios_ml.yield_.model import ModelConfig, YieldModel, assemble
from krishios_ml.yield_.sequences import build as build_sequences

DAILY = DATA_DIR / "processed" / "yield_features" / "v1" / "district_daily"
CACHE = DATA_DIR / "processed" / "yield_features" / "v1" / "sequences.npz"
RUNS = ML_ROOT / "artifacts" / "yield" / "runs"
NUMERIC = [*HISTORY, *WEATHER_Z, *NDVI_Z, "ndvi_good_share"]
META = ["crop_canonical", "tier", "yield", "yield_unit", "hist_mean", "eval_clean"]
LEAD_INDEX = {lead: i for i, lead in enumerate(LEADS)}
GRID = {"hidden": (32, 64, 96), "dropout": (0.1, 0.3), "lr": (3e-4, 1e-3),
        "weight_decay": (1e-3, 1e-2)}


def sequences(labels: pd.DataFrame) -> dict[str, np.ndarray]:
    if not CACHE.exists():
        keys = labels[KEYS].drop_duplicates()
        data = build_sequences(keys, DAILY, pd.read_parquet(MONTHLY))
        np.savez(CACHE, **data)
    with np.load(CACHE) as z:
        return {k: z[k] for k in z.files}


def vocabulary(values: pd.Series) -> dict:
    return {v: i + 1 for i, v in enumerate(sorted(values.unique()))}  # 0 = unseen


def load_frames(labels: pd.DataFrame, feats: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = build_frame(labels, feats)
    frame = frame[frame["split"].isin(["train", "val"]) & frame["eval_ok"]]
    ndvi = pd.read_parquet(SEASON)
    parts = []
    for lead in LEADS:
        f = frame[frame["lead_days"] == lead]
        f = add_anomalies(f, weather_normals(f[f["split"] == "train"]))
        parts.append(add_ndvi(f, ndvi))
    all_rows = pd.concat(parts, ignore_index=True)
    return (all_rows[all_rows["split"] == "train"].reset_index(drop=True),
            all_rows[all_rows["split"] == "val"].reset_index(drop=True))


class Tensors:
    def __init__(self, df: pd.DataFrame, seq_index: dict, vocab: dict, num_stats, device) -> None:
        keys = list(zip(df["lgd_district_code"].astype(int), df["crop_year"].astype(int),
                        df["season"], strict=True))
        self.key = torch.tensor([seq_index[k] for k in keys], device=device)
        x = df[NUMERIC].replace([np.inf, -np.inf], np.nan).to_numpy("float32")
        missing = ~np.isfinite(x)
        x = (x - num_stats[0]) / num_stats[1]
        x[missing] = 0.0
        self.static = torch.tensor(np.hstack([x, missing.astype("float32")]), device=device)
        for name, col in (("crop", "crop_canonical"), ("season", "season"),
                          ("state", "lgd_state_code")):
            ids = df[col].map(vocab[name]).fillna(0).to_numpy("int64")
            setattr(self, name, torch.tensor(ids, device=device))
        self.lead_days = torch.tensor(df["lead_days"].to_numpy("int64"), device=device)
        self.lead_idx = torch.tensor(df["lead_days"].map(LEAD_INDEX).to_numpy("int64"),
                                     device=device)
        self.y = torch.tensor(df["ratio"].clip(*TARGET_CLIP).to_numpy("float32"), device=device)

    def __len__(self) -> int:
        return len(self.y)


def forward(model, t: Tensors, idx, seq, stats) -> torch.Tensor:
    k = t.key[idx]
    x = assemble(seq["weather"][k], seq["ndvi"][k], seq["pub"][k], t.lead_days[idx], stats)
    return model(x, t.static[idx], t.crop[idx], t.season[idx], t.state[idx], t.lead_idx[idx])


@torch.no_grad()
def predict(model, t: Tensors, seq, stats, batch: int = 16_384) -> np.ndarray:
    model.eval()
    out = [forward(model, t, torch.arange(i, min(i + batch, len(t)), device=t.y.device), seq, stats)
           for i in range(0, len(t), batch)]
    return torch.cat(out).clamp_min(0).cpu().numpy()


def evaluate(va: pd.DataFrame, pred: np.ndarray) -> tuple[float, dict]:
    by_lead = {}
    for lead in LEADS:
        m = (va["lead_days"] == lead).to_numpy()
        by_lead[lead] = score(va[m].reset_index(drop=True), pred[m])
    return float(np.mean([r["A"]["nmae_median"] for r in by_lead.values()])), by_lead


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="b5_all")
    ap.add_argument("--seeds", type=int, nargs="*", default=[0, 1, 2])
    ap.add_argument("--hidden", type=int, default=96)
    ap.add_argument("--dropout", type=float, default=0.1)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--batch", type=int, default=2048)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--patience", type=int, default=6)
    ap.add_argument("--grid", action="store_true", help="search GRID with seed 0 first")
    args = ap.parse_args()
    config = {"phase": "val", **vars(args), "leads": list(LEADS), "numeric": NUMERIC,
              "loss": "huber(0.5) on clipped ratio", "metric": "mean over leads of tier-A "
              "median nMAE"}
    labels, feats = pd.read_parquet(LABELS), pd.read_parquet(FEATURES)
    raw = sequences(labels)
    tr, va = load_frames(labels, feats)
    del feats
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    seq_index = {k: i for i, k in enumerate(zip(raw["lgd_district_code"].tolist(),
                                                raw["crop_year"].tolist(),
                                                raw["season"].tolist(), strict=True))}
    train_keys = np.unique([seq_index[k] for k in zip(
        tr["lgd_district_code"].astype(int), tr["crop_year"].astype(int), tr["season"],
        strict=True)])
    w, n = raw["weather"][train_keys], raw["ndvi"][train_keys]
    stats = {k: torch.tensor(v, device=device, dtype=torch.float32) for k, v in {
        "w_mu": np.nanmean(w, axis=(0, 1)), "w_sd": np.nanstd(w, axis=(0, 1)),
        "n_mu": np.nanmean(n, axis=(0, 1)), "n_sd": np.nanstd(n, axis=(0, 1))}.items()}
    seq = {"weather": torch.tensor(raw["weather"], device=device),
           "ndvi": torch.tensor(raw["ndvi"], device=device),
           "pub": torch.tensor(raw["ndvi_pub"].astype("int64"), device=device)}
    x = tr[NUMERIC].replace([np.inf, -np.inf], np.nan).to_numpy("float32")
    num_stats = (np.nanmean(x, axis=0), np.nanstd(x, axis=0).clip(1e-6))
    vocab = {"crop": vocabulary(tr["crop_canonical"]), "season": vocabulary(tr["season"]),
             "state": vocabulary(tr["lgd_state_code"])}
    t_tr = Tensors(tr, seq_index, vocab, num_stats, device)
    t_va = Tensors(va, seq_index, vocab, num_stats, device)
    va_meta = va[["lead_days", *META]].copy()
    del tr, va, x, w, n, raw
    def train_one(p: dict, seed: int, quiet: bool = False):
        cfg = ModelConfig(n_static=2 * len(NUMERIC), n_crops=len(vocab["crop"]) + 1,
                          n_seasons=len(vocab["season"]) + 1, n_states=len(vocab["state"]) + 1,
                          hidden=p["hidden"], dropout=p["dropout"])
        torch.manual_seed(seed)
        model = YieldModel(cfg).to(device)
        opt = torch.optim.AdamW(model.parameters(), lr=p["lr"], weight_decay=p["weight_decay"])
        steps = len(t_tr) // args.batch
        sched = torch.optim.lr_scheduler.OneCycleLR(opt, p["lr"], total_steps=args.epochs * steps)
        scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
        best, best_epoch, bad, state, t0 = np.inf, -1, 0, None, time.time()
        g = torch.Generator(device=device).manual_seed(seed)
        for epoch in range(args.epochs):
            model.train()
            order = torch.randperm(len(t_tr), generator=g, device=device)
            total = 0.0
            for b in range(steps):
                idx = order[b * args.batch:(b + 1) * args.batch]
                with torch.amp.autocast("cuda", enabled=device.type == "cuda"):
                    loss = torch.nn.functional.huber_loss(
                        forward(model, t_tr, idx, seq, stats), t_tr.y[idx], delta=0.5)
                opt.zero_grad(set_to_none=True)
                scaler.scale(loss).backward()
                scaler.step(opt)
                scaler.update()
                sched.step()
                total += float(loss.detach())
            val, _ = evaluate(va_meta, predict(model, t_va, seq, stats))
            if not quiet:
                print(f"seed {seed} epoch {epoch}: loss {total / steps:.4f} val {val:.4f}",
                      flush=True)
            if val < best - 1e-4:
                best, best_epoch, bad = val, epoch, 0
                state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            else:
                bad += 1
                if bad >= args.patience:
                    break
        model.load_state_dict(state)
        _, by_lead = evaluate(va_meta, predict(model, t_va, seq, stats))
        info = {"seed": seed, "best_epoch": best_epoch, "val": best,
                "seconds": round(time.time() - t0, 1)}
        ckpt = {"state_dict": state, "config": model.config, "epoch": best_epoch}
        del model, opt
        torch.cuda.empty_cache()
        return info, by_lead, ckpt

    base = {k: getattr(args, k) for k in ("hidden", "dropout", "lr", "weight_decay")}
    runs: dict[int, list[dict]] = {lead: [] for lead in LEADS}
    summary, search = [], []
    with track_experiment("yield_b5", config, seed=None,
                          split_id="apy-tierv2-ee75501cc5ef") as rec:
        out_dir = RUNS / rec.run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        if args.grid:
            for values in itertools.product(*GRID.values()):
                p = dict(zip(GRID, values, strict=True))
                info, _, _ = train_one(p, 0, quiet=True)
                search.append({**p, **info})
                print(json.dumps(search[-1]), flush=True)
            base = {k: min(search, key=lambda r: r["val"])[k] for k in GRID}
            print("selected", json.dumps(base), flush=True)
        for seed in args.seeds:
            info, by_lead, ckpt = train_one(base, seed)
            torch.save(ckpt, out_dir / f"{args.name}_seed{seed}.pt")
            for lead in LEADS:
                runs[lead].append(by_lead[lead])
            summary.append(info)
        results = {str(lead): {"A": mean_std(r, "A"), "B": mean_std(r, "B"),
                               "A_all": mean_std(r, "A_all"), "seeds": len(r),
                               "per_crop_seed0": r[0]["per_crop"]} for lead, r in runs.items()}
        rec.metrics = {lead: {"A_median": r["A"]["nmae_median"]["mean"],
                              "A_worst_decile": r["A"]["nmae_worst_decile"]["mean"],
                              "B_median": r["B"]["nmae_median"]["mean"]}
                       for lead, r in results.items()}
        torch.save({"stats": {k: v.cpu() for k, v in stats.items()}, "numeric": NUMERIC,
                    "num_stats": num_stats, "vocab": vocab}, out_dir / "preprocessing.pt")
        path = REPORTS_DIR / "data" / f"yield_b5_val_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config, "selected": base,
                                    "search": search, "seeds": summary, "results": results},
                                   indent=1, default=float),
                        encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
    print(json.dumps(rec.metrics, indent=1))
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
