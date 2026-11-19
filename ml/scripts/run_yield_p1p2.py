"""Phase 10 experiments P1 and P2 for B5, the shared yield model (validation years only).

P1, self-supervised pretraining (RQ1). The temporal encoder (the GRU over weather and NDVI dekads)
is pretrained on the input timelines of the training years only, with no yields:

- ``mask``: masked reconstruction. 30% of the available dekads are hidden and reconstructed.
- ``xmodal``: cross-modal prediction. One whole input (weather or NDVI) is hidden and predicted
  from the other.
- ``both``: the two objectives on alternate batches.
- ``none``: no pretraining (the baseline).

Each variant is then fine-tuned on 10, 25, 50 and 100% of the training district-seasons (the
same subset for every variant at a given seed), with the same optimizer budget in steps, which
gives label-efficiency curves.

P2, modality dropout (RQ3). During training, weather, NDVI and yield history are each hidden for
a sample with probability ``p``. Models trained with and without it are scored on the validation
years under each missing-input condition.

Leakage controls: the test splits are dropped before any tensor is built (and are not in the Colab
bundle at all); pretraining sees only training-year inputs; early stopping and selection use the
validation years, as in ``run_yield_b5.py``. Metric: mean over leads of tier-A median nMAE.

Usage (from ml/)::

    uv run --no-sync python scripts/run_yield_p1p2.py --experiment p1
    uv run --no-sync python scripts/run_yield_p1p2.py --experiment p2
    uv run --no-sync python scripts/run_yield_p1p2.py --smoke    # 1 epoch each, pipeline check

``--progress FILE`` keeps finished runs (one JSON line each) so an interrupted job resumes.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
import torch
from run_yield_b5 import NUMERIC, Tensors, evaluate, load_frames, sequences, vocabulary
from run_yield_baselines import FEATURES, LABELS, LEADS
from torch import nn

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, REPORTS_DIR
from krishios_ml.yield_.data import HISTORY, NDVI_Z, WEATHER_Z
from krishios_ml.yield_.model import ModelConfig, YieldModel, assemble

SPLIT_ID = "apy-tierv2-ee75501cc5ef"
# Selected by the B5 grid search on validation (run 6df72643cd82).
BEST = {"hidden": 64, "dropout": 0.3, "lr": 3e-4, "weight_decay": 1e-3}
VARIANTS = ("none", "mask", "xmodal", "both")
FRACTIONS = (0.1, 0.25, 0.5, 1.0)
N_W, N_N = 5, 2  # weather and NDVI channels in the assembled sequence
COLS = {
    "weather": [NUMERIC.index(c) for c in WEATHER_Z],
    "ndvi": [NUMERIC.index(c) for c in [*NDVI_Z, "ndvi_good_share"]],
    "history": [NUMERIC.index(c) for c in HISTORY],
}
CONDITIONS = {  # input hidden at forecast time: (weather, ndvi, history)
    "full": (False, False, False),
    "no_ndvi": (False, True, False),
    "no_weather": (True, False, False),
    "no_history": (False, False, True),
    "history_only": (True, True, False),
}


class Setup:
    """Tensors for the training and validation years, built exactly as in run_yield_b5.py."""

    def __init__(self, device: torch.device) -> None:
        labels, feats = pd.read_parquet(LABELS), pd.read_parquet(FEATURES)
        raw = sequences(labels)
        tr, va = load_frames(labels, feats)
        del feats
        self.device = device
        seq_index = {k: i for i, k in enumerate(zip(raw["lgd_district_code"].tolist(),
                                                    raw["crop_year"].tolist(),
                                                    raw["season"].tolist(), strict=True))}
        self.train_keys = np.unique([seq_index[k] for k in zip(
            tr["lgd_district_code"].astype(int), tr["crop_year"].astype(int), tr["season"],
            strict=True)])
        w, n = raw["weather"][self.train_keys], raw["ndvi"][self.train_keys]
        self.stats = {k: torch.tensor(v, device=device, dtype=torch.float32) for k, v in {
            "w_mu": np.nanmean(w, axis=(0, 1)), "w_sd": np.nanstd(w, axis=(0, 1)),
            "n_mu": np.nanmean(n, axis=(0, 1)), "n_sd": np.nanstd(n, axis=(0, 1))}.items()}
        self.seq = {"weather": torch.tensor(raw["weather"], device=device),
                    "ndvi": torch.tensor(raw["ndvi"], device=device),
                    "pub": torch.tensor(raw["ndvi_pub"].astype("int64"), device=device)}
        x = tr[NUMERIC].replace([np.inf, -np.inf], np.nan).to_numpy("float32")
        num_stats = (np.nanmean(x, axis=0), np.nanstd(x, axis=0).clip(1e-6))
        self.vocab = {"crop": vocabulary(tr["crop_canonical"]),
                      "season": vocabulary(tr["season"]),
                      "state": vocabulary(tr["lgd_state_code"])}
        self.t_tr = Tensors(tr, seq_index, self.vocab, num_stats, device)
        self.t_va = Tensors(va, seq_index, self.vocab, num_stats, device)
        self.va_meta = va[["lead_days", "crop_canonical", "tier", "yield", "yield_unit",
                           "hist_mean", "eval_clean"]].copy()
        col_mask = torch.zeros(3, len(NUMERIC), dtype=torch.bool, device=device)
        for i, name in enumerate(("weather", "ndvi", "history")):
            col_mask[i, COLS[name]] = True
        self.col_mask = col_mask
        self.train_key_t = torch.tensor(self.train_keys, device=device)

    def config(self, p: dict) -> ModelConfig:
        return ModelConfig(n_static=2 * len(NUMERIC), n_crops=len(self.vocab["crop"]) + 1,
                           n_seasons=len(self.vocab["season"]) + 1,
                           n_states=len(self.vocab["state"]) + 1, hidden=p["hidden"],
                           dropout=p["dropout"])


def hide(x: torch.Tensor, static: torch.Tensor, drop: torch.Tensor,
         col_mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Hide inputs per sample. ``drop`` is (batch, 3) for weather, NDVI, history. A hidden
    timeline gets value 0 and mask 0; hidden static columns get value 0 and missing flag 1,
    which is how the model already sees inputs that do not exist."""
    keep_w = (~drop[:, 0]).float()[:, None, None]
    keep_n = (~drop[:, 1]).float()[:, None, None]
    x = torch.cat([x[..., :N_W] * keep_w, x[..., N_W:N_W + N_N] * keep_n,
                   x[..., N_W + N_N:N_W + N_N + 1] * keep_w, x[..., -1:] * keep_n], dim=-1)
    cols = (drop.float() @ col_mask.float()) > 0  # (batch, n_numeric)
    n = col_mask.shape[1]
    values = torch.where(cols, torch.zeros_like(static[:, :n]), static[:, :n])
    flags = torch.where(cols, torch.ones_like(static[:, n:]), static[:, n:])
    return x, torch.cat([values, flags], dim=1)


def run_model(model, s: Setup, t: Tensors, idx, drop: torch.Tensor | None) -> torch.Tensor:
    k = t.key[idx]
    x = assemble(s.seq["weather"][k], s.seq["ndvi"][k], s.seq["pub"][k], t.lead_days[idx],
                 s.stats)
    static = t.static[idx]
    if drop is not None:
        x, static = hide(x, static, drop, s.col_mask)
    return model(x, static, t.crop[idx], t.season[idx], t.state[idx], t.lead_idx[idx])


@torch.no_grad()
def predict(model, s: Setup, condition: tuple[bool, bool, bool] = (False, False, False),
            batch: int = 16_384) -> np.ndarray:
    model.eval()
    t, out = s.t_va, []
    for i in range(0, len(t), batch):
        idx = torch.arange(i, min(i + batch, len(t)), device=s.device)
        drop = None
        if any(condition):
            drop = torch.tensor(condition, device=s.device).expand(len(idx), 3)
        out.append(run_model(model, s, t, idx, drop))
    return torch.cat(out).clamp_min(0).float().cpu().numpy()


def summary(va_meta: pd.DataFrame, pred: np.ndarray) -> dict:
    val, by_lead = evaluate(va_meta, pred)
    return {"val": val,
            "A_worst_decile": float(np.mean([r["A"]["nmae_worst_decile"]
                                             for r in by_lead.values()])),
            "B_median": float(np.mean([r["B"]["nmae_median"] for r in by_lead.values()])),
            "by_lead": {str(lead): r["A"]["nmae_median"] for lead, r in by_lead.items()}}


def pretrain(s: Setup, variant: str, seed: int, p: dict, epochs: int, batch: int) -> dict:
    """Pretrain the GRU on training-year inputs only; returns its state dict and the loss."""
    torch.manual_seed(seed)
    enc = YieldModel(s.config(p)).temporal.to(s.device)
    dec = nn.Linear(p["hidden"], N_W + N_N).to(s.device)
    opt = torch.optim.AdamW([*enc.parameters(), *dec.parameters()], lr=1e-3, weight_decay=1e-4)
    leads = torch.tensor(LEADS, device=s.device)
    g = torch.Generator(device=s.device).manual_seed(seed)
    keys, step, last = s.train_key_t, 0, math.nan
    for _ in range(epochs):
        order = keys[torch.randperm(len(keys), generator=g, device=s.device)]
        total, count = 0.0, 0
        for b in range(0, len(order), batch):
            k = order[b:b + batch]
            lead = leads[torch.randint(len(LEADS), (len(k),), generator=g, device=s.device)]
            x = assemble(s.seq["weather"][k], s.seq["ndvi"][k], s.seq["pub"][k], lead, s.stats)
            w_ok, n_ok = x[..., N_W + N_N] > 0, x[..., -1] > 0
            objective = variant if variant != "both" else ("mask", "xmodal")[step % 2]
            if objective == "mask":
                m = torch.rand(w_ok.shape, generator=g, device=s.device) < 0.3
                hide_w, hide_n = m & w_ok, m & n_ok
            else:  # hide one whole input per sample
                ndvi = (torch.rand(len(k), generator=g, device=s.device) < 0.5)[:, None]
                hide_w, hide_n = ~ndvi & w_ok, ndvi & n_ok
            xin = torch.cat([x[..., :N_W] * (~hide_w)[..., None],
                             x[..., N_W:N_W + N_N] * (~hide_n)[..., None],
                             (w_ok & ~hide_w)[..., None].float(),
                             (n_ok & ~hide_n)[..., None].float()], dim=-1)
            out, _ = enc(xin)
            err = (dec(out) - x[..., :N_W + N_N]) ** 2
            loss = ((err[..., :N_W].mean(-1) * hide_w).sum() / hide_w.sum().clamp_min(1)
                    + (err[..., N_W:].mean(-1) * hide_n).sum() / hide_n.sum().clamp_min(1))
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            total, count, step = total + float(loss.detach()), count + 1, step + 1
        last = total / max(count, 1)
    return {"state": {k: v.detach().clone() for k, v in enc.state_dict().items()},
            "loss": last}


def finetune(s: Setup, p: dict, seed: int, args, init: dict | None = None,
             fraction: float = 1.0, modality_drop: float = 0.0):
    """Train B5 as in run_yield_b5.py. ``fraction`` < 1 keeps that share of training
    district-seasons; epochs and patience scale up so the number of optimizer steps matches."""
    t = s.t_tr
    rows = torch.arange(len(t), device=s.device)
    if fraction < 1.0:
        keys = np.random.default_rng(10_000 + seed).permutation(s.train_keys)
        chosen = torch.tensor(keys[:math.ceil(fraction * len(keys))], device=s.device)
        rows = rows[torch.isin(t.key, chosen)]
    epochs = max(1, round(args.epochs / fraction))
    patience = max(1, round(args.patience / fraction))
    steps = max(1, len(rows) // args.batch)
    torch.manual_seed(seed)
    model = YieldModel(s.config(p)).to(s.device)
    if init is not None:
        model.temporal.load_state_dict(init)
        loaded = model.temporal.state_dict()
        if not all(torch.equal(loaded[k], v.to(loaded[k].device)) for k, v in init.items()):
            raise RuntimeError("pretrained encoder weights were not loaded")
    opt = torch.optim.AdamW(model.parameters(), lr=p["lr"], weight_decay=p["weight_decay"])
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, p["lr"], total_steps=epochs * steps)
    cuda = s.device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=cuda)
    g = torch.Generator(device=s.device).manual_seed(seed)
    best, best_epoch, bad, state, t0 = np.inf, -1, 0, None, time.time()
    for epoch in range(epochs):
        model.train()
        order = rows[torch.randperm(len(rows), generator=g, device=s.device)]
        for b in range(steps):
            idx = order[b * args.batch:(b + 1) * args.batch]
            drop = None
            if modality_drop > 0:
                drop = torch.rand(len(idx), 3, generator=g, device=s.device) < modality_drop
            with torch.amp.autocast("cuda", enabled=cuda):
                loss = nn.functional.huber_loss(run_model(model, s, t, idx, drop), t.y[idx],
                                                delta=0.5)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
        val, _ = evaluate(s.va_meta, predict(model, s))
        if val < best - 1e-4:
            best, best_epoch, bad = val, epoch, 0
            state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                break
    model.load_state_dict(state)
    info = {"best_epoch": best_epoch, "epochs_allowed": epochs, "train_rows": len(rows),
            "seconds": round(time.time() - t0, 1)}
    return model, info


class Progress:
    """Finished runs, one JSON line each, so an interrupted job can resume."""

    def __init__(self, path: Path | None) -> None:
        self.path, self.rows = path, {}
        if path and path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                self.rows[r["key"]] = r

    def get(self, key: str) -> dict | None:
        return self.rows.get(key)

    def put(self, key: str, row: dict) -> dict:
        row = {"key": key, **row}
        self.rows[key] = row
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row) + "\n")
        return row


def stat(values: list[float]) -> dict:
    a = np.asarray(values, dtype=float)
    return {"mean": float(a.mean()), "sd": float(a.std(ddof=1)) if len(a) > 1 else 0.0,
            "n": len(a)}


def paired(rows: list[dict], base: list[dict], key: str = "val") -> dict:
    """Difference against the baseline at the same seed (negative = better)."""
    b = {r["seed"]: r[key] for r in base}
    d = [r[key] - b[r["seed"]] for r in rows if r["seed"] in b]
    return {**stat(d), "wins": int(sum(x < 0 for x in d))} if d else {}


def experiment_p1(s: Setup, args, prog: Progress, prefix: str) -> dict:
    runs: list[dict] = []
    for seed in args.seeds:
        for variant in args.variants:
            init, pre_loss = None, None
            for fraction in args.fractions:
                key = f"{prefix}p1|{variant}|{fraction}|{seed}"
                if (row := prog.get(key)) is None:
                    if variant != "none" and init is None:
                        pre = pretrain(s, variant, seed, BEST, args.pretrain_epochs, 1024)
                        init, pre_loss = pre["state"], pre["loss"]
                    model, info = finetune(s, BEST, seed, args, init=init, fraction=fraction)
                    row = prog.put(key, {"variant": variant, "fraction": fraction, "seed": seed,
                                         "pretrain_loss": pre_loss, **info,
                                         **summary(s.va_meta, predict(model, s))})
                    del model
                    if s.device.type == "cuda":
                        torch.cuda.empty_cache()
                print(f"P1 {variant:6s} {fraction:>4} seed {seed}: val {row['val']:.4f} "
                      f"(epoch {row['best_epoch']}, {row['seconds']} s)", flush=True)
                runs.append(row)
    table: dict = {}
    for variant in args.variants:
        for fraction in args.fractions:
            rows = [r for r in runs if r["variant"] == variant and r["fraction"] == fraction]
            base = [r for r in runs if r["variant"] == "none" and r["fraction"] == fraction]
            table.setdefault(variant, {})[str(fraction)] = {
                "val": stat([r["val"] for r in rows]),
                "A_worst_decile": stat([r["A_worst_decile"] for r in rows]),
                "B_median": stat([r["B_median"] for r in rows]),
                "vs_none": paired(rows, base) if variant != "none" else None}
    return {"table": table, "runs": runs}


def experiment_p2(s: Setup, args, prog: Progress, prefix: str) -> dict:
    runs: list[dict] = []
    for seed in args.seeds:
        for p_drop in (0.0, args.modality_drop):
            key = f"{prefix}p2|{p_drop}|{seed}"
            if (row := prog.get(key)) is None:
                model, info = finetune(s, BEST, seed, args, modality_drop=p_drop)
                scores = {name: summary(s.va_meta, predict(model, s, cond))
                          for name, cond in CONDITIONS.items()}
                row = prog.put(key, {"modality_drop": p_drop, "seed": seed, **info,
                                     "conditions": scores})
                del model
                if s.device.type == "cuda":
                    torch.cuda.empty_cache()
            print(f"P2 drop {p_drop} seed {seed}: " + ", ".join(
                f"{c} {v['val']:.4f}" for c, v in row["conditions"].items()), flush=True)
            runs.append(row)
    table: dict = {}
    for name in CONDITIONS:
        for p_drop in (0.0, args.modality_drop):
            rows = [{"seed": r["seed"], **r["conditions"][name]} for r in runs
                    if r["modality_drop"] == p_drop]
            base = [{"seed": r["seed"], **r["conditions"][name]} for r in runs
                    if r["modality_drop"] == 0.0]
            table.setdefault(name, {})[str(p_drop)] = {
                "val": stat([r["val"] for r in rows]),
                "A_worst_decile": stat([r["A_worst_decile"] for r in rows]),
                "B_median": stat([r["B_median"] for r in rows]),
                "vs_no_dropout": paired(rows, base) if p_drop else None}
    return {"table": table, "runs": runs}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", choices=("p1", "p2", "both"), default="both")
    ap.add_argument("--seeds", type=int, nargs="*", default=[0, 1, 2, 3, 4])
    ap.add_argument("--variants", nargs="*", default=list(VARIANTS))
    ap.add_argument("--fractions", type=float, nargs="*", default=list(FRACTIONS))
    ap.add_argument("--modality-drop", type=float, default=0.25)
    ap.add_argument("--pretrain-epochs", type=int, default=30)
    ap.add_argument("--batch", type=int, default=2048)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--patience", type=int, default=6)
    ap.add_argument("--progress", type=Path, default=None)
    ap.add_argument("--smoke", action="store_true", help="tiny run to check the pipeline")
    args = ap.parse_args()
    if "none" not in args.variants:
        args.variants = ["none", *args.variants]
    log_path, out_dir, prefix = None, REPORTS_DIR / "data", ""
    if args.smoke:  # kept out of the experiment log and the reports
        args.seeds, args.variants, args.fractions = [0], ["none", "both"], [0.25, 1.0]
        args.epochs, args.patience, args.pretrain_epochs = 1, 1, 1
        out_dir = DATA_DIR / "interim" / "smoke"
        log_path, prefix = out_dir / "smoke.jsonl", "smoke|"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("device", device, flush=True)
    s = Setup(device)
    prog = Progress(args.progress)
    todo = ("p1", "p2") if args.experiment == "both" else (args.experiment,)
    for name in todo:
        config = {"phase": "val", "experiment": name, "params": BEST,
                  **{k: v for k, v in vars(args).items() if k != "progress"},
                  "leads": list(LEADS), "metric": "mean over leads of tier-A median nMAE",
                  "conditions": CONDITIONS if name == "p2" else None,
                  "device": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu"}
        with track_experiment(f"yield_{name}", config, seed=None, split_id=SPLIT_ID,
                              log_path=log_path) as rec:
            run = experiment_p1 if name == "p1" else experiment_p2
            out = run(s, args, prog, prefix)
            rec.metrics = {k: {kk: vv["val"]["mean"] for kk, vv in v.items()}
                           for k, v in out["table"].items()}
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"yield_{name}_val_{rec.run_id}.json"
            path.write_text(json.dumps({"run_id": rec.run_id, "config": config, **out},
                                       indent=1, default=float), encoding="utf-8")
            rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
        print(json.dumps(out["table"], indent=1, default=float))
        print(f"{name} run_id {rec.run_id}", flush=True)


if __name__ == "__main__":
    main()
