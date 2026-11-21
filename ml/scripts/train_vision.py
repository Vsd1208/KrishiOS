"""Phase 9: train + evaluate the crop / condition model (two experiments x 3 seeds).

- **E1 all:** train on every source's train split (PlantVillage lab + PlantDoc + India rice).
- **E2 lab_only:** train on PlantVillage only. Scored on the same field tests, this measures
  how lab-only training transfers to field photos (reported honestly).
- **E3_india:** E1 plus the checked Indian field photos (``prepare_india_vision.py``; adds
  chilli and wheat). Needs ``--with-india``. Its test split is scored once, like the others.

``--progress-dir`` keeps each finished experiment x seed (results and weights) and skips it when
the same configuration is run again, so an interrupted run (for example a Colab disconnect)
loses only the seed in progress.

Model selection uses each experiment's own validation data (E1: field validation; E2: lab
validation, so no field information leaks into the lab-only model). Temperatures are fitted
on validation. Test sets (field: PlantDoc test + India rice test; lab: PlantVillage test) are
scored once per configuration: a second run of the same configuration is refused.

Usage (from ml/)::

    uv run --no-sync python scripts/train_vision.py --epochs 8
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

from krishios_ml.common.experiment_log import read_records, track_experiment
from krishios_ml.common.paths import DATA_DIR, EXPERIMENTS_DIR, ML_ROOT, REPORTS_DIR
from krishios_ml.vision import metrics as vm
from krishios_ml.vision.train import TrainConfig, fit, predict_logits

DATA = DATA_DIR / "processed" / "vision" / "v1"
RUNS = ML_ROOT / "artifacts" / "vision" / "runs"
SEEDS = (0, 1, 2)
EXPERIMENTS = {
    "E1_all": {"train_sources": ("plantvillage", "plantdoc", "agml_rice_india"),
               "select_on": "field"},
    "E2_lab_only": {"train_sources": ("plantvillage",), "select_on": "lab"},
    "E3_india": {"train_sources": ("plantvillage", "plantdoc", "agml_rice_india", "india_field"),
                 "select_on": "field"},
}
INDIA = DATA_DIR / "processed" / "vision" / "india_v1" / "images.parquet"
CONFIRM_THRESHOLD = 0.6


def encode(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str], np.ndarray]:
    crops = sorted(df["crop_label"].unique())
    conds = sorted((df["crop_label"] + "|" + df["condition"]).unique())
    ci, di = {c: i for i, c in enumerate(crops)}, {c: i for i, c in enumerate(conds)}
    df = df.assign(crop_idx=df["crop_label"].map(ci),
                   cond_idx=(df["crop_label"] + "|" + df["condition"]).map(di))
    crop_of_cond = np.array([ci[c.split("|")[0]] for c in conds])
    return df, crops, conds, crop_of_cond


def make_score(setting: str, crop_of_cond: np.ndarray):
    def score(val: pd.DataFrame, crop_l: np.ndarray, cond_l: np.ndarray) -> float:
        m = (val["setting"] == setting).to_numpy()
        if not m.any():
            m = np.ones(len(val), dtype=bool)
        yc, yd = val["crop_idx"].to_numpy()[m], val["cond_idx"].to_numpy()[m]
        crop_acc = float((crop_l[m].argmax(1) == yc).mean())
        cond_f1 = vm.macro_f1(cond_l[m].argmax(1), yd)
        return (crop_acc + cond_f1) / 2

    return score


def evaluate(rows: pd.DataFrame, crop_l, cond_l, t_crop, t_cond, crop_of_cond) -> dict:
    yc, yd = rows["crop_idx"].to_numpy(), rows["cond_idx"].to_numpy()
    out = {"crop": vm.summary(crop_l, yc, t_crop), "condition": vm.summary(cond_l, yd, t_cond)}
    oracle = vm.conditional_condition(cond_l, crop_of_cond, yc)  # crop confirmed by farmer
    out["condition_given_crop"] = vm.summary(oracle, yd, t_cond)
    p = vm.softmax(crop_l, t_crop)
    conf = p.max(1)
    auto = conf >= CONFIRM_THRESHOLD
    out["crop_auto_accept"] = {
        "threshold": CONFIRM_THRESHOLD, "share": float(auto.mean()),
        "accuracy_when_auto": float((p.argmax(1)[auto] == yc[auto]).mean()) if auto.any()
        else None,
        "accuracy_when_confirm": float((p.argmax(1)[~auto] == yc[~auto]).mean())
        if (~auto).any() else None,
    }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--backbone", default="efficientnet_b0.ra_in1k")
    ap.add_argument("--experiments", nargs="*", default=list(EXPERIMENTS))
    ap.add_argument("--seeds", nargs="*", type=int, default=list(SEEDS))
    ap.add_argument("--with-india", action="store_true",
                    help="add the Indian field photos (needed by E3_india)")
    ap.add_argument("--progress-dir", type=Path, default=None,
                    help="keep finished experiment x seed results here and resume from them")
    args = ap.parse_args()
    df = pd.read_parquet(DATA / "images.parquet")
    df["cache"] = df["cache"].str.replace("\\", "/", regex=False)
    if args.with_india:
        df = pd.concat([df, pd.read_parquet(INDIA)], ignore_index=True)
    elif "E3_india" in args.experiments:
        raise SystemExit("E3_india needs --with-india")
    df, crops, conds, crop_of_cond = encode(df)
    config = {"backbone": args.backbone, "epochs": args.epochs, "seeds": args.seeds,
              "experiments": {k: EXPERIMENTS[k] for k in args.experiments},
              "dataset_rows": len(df), "crops": crops, "n_conditions": len(conds),
              "confirm_threshold": CONFIRM_THRESHOLD}
    if args.with_india:
        config["with_india"] = True
    config["config_hash"] = hashlib.sha256(json.dumps(config, sort_keys=True,
                                                      default=str).encode()).hexdigest()[:12]
    log_path = EXPERIMENTS_DIR / "vision_train.jsonl"
    if log_path.exists() and any(r["config"].get("config_hash") == config["config_hash"]
                                 for r in read_records(log_path)):
        raise SystemExit("this configuration was already trained and tested; refusing to "
                         "score the test sets again")
    train, val, test = (df[df["split"] == s].reset_index(drop=True)
                        for s in ("train", "val", "test"))
    with track_experiment("vision_train", config, seed=None,
                          split_id="krishios-vision-v1") as rec:
        import torch
        from torch.utils.data import DataLoader

        from krishios_ml.vision.train import ImageSet, _transforms

        results: dict = {}
        out_dir = RUNS / rec.run_id
        progress = (args.progress_dir / config["config_hash"]) if args.progress_dir else None
        if progress:
            progress.mkdir(parents=True, exist_ok=True)
            for f in sorted(progress.glob("*_seed*.json")):  # file E1_all_seed0 = key E1_all:seed0
                exp_name, seed_no = f.stem.rsplit("_seed", 1)
                results[f"{exp_name}:seed{seed_no}"] = json.loads(f.read_text(encoding="utf-8"))
            if results:
                print(f"resuming: {sorted(results)} already done", flush=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        for exp in args.experiments:
            spec = EXPERIMENTS[exp]
            val_exp = val[val["source"].isin(spec["train_sources"])].reset_index(drop=True)
            for seed in args.seeds:
                if f"{exp}:seed{seed}" in results:
                    continue
                cfg = TrainConfig(backbone=args.backbone, epochs=args.epochs, seed=seed,
                                  train_sources=spec["train_sources"])
                fitted = fit(cfg, train, val_exp, DATA / "cache", len(crops), len(conds),
                             make_score(spec["select_on"], crop_of_cond))
                device = next(fitted.model.parameters()).device
                dc = fitted.data_config
                _, tf_eval = _transforms(cfg, dc["mean"], dc["std"])

                def logits(rows: pd.DataFrame, model=fitted.model, tf=tf_eval, dev=device,
                           workers=cfg.num_workers):
                    dl = DataLoader(ImageSet(rows, DATA / "cache", tf), batch_size=128,
                                    num_workers=workers)
                    return predict_logits(model, dl, dev)

                vc, vd = logits(val_exp)
                t_crop = vm.fit_temperature(vc, val_exp["crop_idx"].to_numpy())
                t_cond = vm.fit_temperature(vd, val_exp["cond_idx"].to_numpy())
                tc, td = logits(test)
                res = {"best_epoch": fitted.best_epoch, "seconds": round(fitted.seconds, 1),
                       "history": fitted.history, "temperature": {"crop": t_crop,
                                                                  "condition": t_cond}}
                for name, m in {"field": test["setting"] == "field",
                                "lab": test["setting"] == "lab",
                                **{f"source:{s}": test["source"] == s
                                   for s in test["source"].unique()}}.items():
                    m = m.to_numpy()
                    if m.any():
                        res[name] = evaluate(test[m], tc[m], td[m], t_crop, t_cond,
                                             crop_of_cond)
                results[f"{exp}:seed{seed}"] = res
                torch.save({"state_dict": fitted.model.state_dict(), "backbone": args.backbone,
                            "crops": crops, "conditions": conds, "data_config": dc,
                            "temperature": {"crop": t_crop, "condition": t_cond},
                            "val_score": max(h["val_score"] for h in fitted.history)},
                           (progress or out_dir) / f"{exp}_seed{seed}.pt")
                if progress:  # written last, so a partial seed is never taken as done
                    tmp = progress / f"{exp}_seed{seed}.part"
                    tmp.write_text(json.dumps(res, default=str), encoding="utf-8")
                    tmp.replace(progress / f"{exp}_seed{seed}.json")
                print(exp, seed, "field crop top1",
                      round(res.get("field", {}).get("crop", {}).get("top1", float("nan")), 4),
                      flush=True)
                del fitted
                torch.cuda.empty_cache()
        if progress:  # the run folder gets every seed's weights, resumed ones included
            import shutil

            for pt in progress.glob("*.pt"):
                shutil.copy2(pt, out_dir / pt.name)
        rec.metrics = {k: {s: {"crop_top1": v[s]["crop"]["top1"],
                               "cond_given_crop_f1": v[s]["condition_given_crop"]["macro_f1"]}
                           for s in ("field", "lab") if s in v} for k, v in results.items()}
        path = REPORTS_DIR / "data" / f"vision_train_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config,
                                    "results": results}, indent=1, default=str),
                        encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
