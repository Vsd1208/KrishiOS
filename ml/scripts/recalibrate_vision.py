"""Phase 9: refit confidence on field validation photos only (no retraining).

The training run fitted temperatures on a validation set that is mostly lab photos, and its
field test confidence was poorly calibrated. Here, for each all-data checkpoint:

- crop temperature: fitted on field validation rows;
- condition temperature: fitted on field validation rows with logits limited to the true crop,
  which is how the provider reads a condition;
- confirmation threshold: the lowest at which auto-accepted crops reach 95% accuracy on PlantDoc
  validation rows (the harder field source), counting only crops the app can auto-accept.

Everything is chosen on validation. The test rows are then scored with the old and new values.
They were already seen by the training run, so these are reported as a separate, labelled
recalibration result. A configuration is scored only once.

Usage (from ml/)::

    uv run --no-sync python scripts/recalibrate_vision.py --run <train_run_id>
"""

from __future__ import annotations

import argparse
import hashlib
import json

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
from train_vision import DATA, RUNS, encode, evaluate

from krishios_ml.common.experiment_log import read_records, track_experiment
from krishios_ml.common.paths import EXPERIMENTS_DIR, REPORTS_DIR
from krishios_ml.vision import metrics as vm
from krishios_ml.vision.train import ImageSet, TrainConfig, _transforms, build_model, predict_logits

TARGET_ACCURACY = 0.95
OLD_THRESHOLD = 0.6
SEEDS = (0, 1, 2)


def app_auto_accept(crop_logits: np.ndarray, y: np.ndarray, t: float, supported: np.ndarray,
                    threshold: float | None) -> dict:
    """What the app does: accept a crop without asking only if it is a supported crop and the
    confidence reaches the threshold. Every other photo gets a confirmation question."""
    p = vm.softmax(crop_logits, t)
    pred, conf = p.argmax(1), p.max(1)
    auto = supported[pred] & (conf >= (np.inf if threshold is None else threshold))
    return {"threshold": threshold, "n": len(y), "share_auto": float(auto.mean()),
            "accuracy_when_auto": float((pred[auto] == y[auto]).mean()) if auto.any() else None,
            "wrong_auto_share_of_all": float((pred[auto] != y[auto]).sum() / len(y))}


def main() -> None:
    import torch
    from torch.utils.data import DataLoader

    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    args = ap.parse_args()
    df, crops, conds, crop_of_cond = encode(pd.read_parquet(DATA / "images.parquet"))
    keys = df.loc[df["crop_canonical"] != "", "crop_label"].unique()
    supported = np.array([c in set(keys) for c in crops])
    config = {"train_run": args.run, "seeds": list(SEEDS), "fit_on": "field validation",
              "target_accuracy": TARGET_ACCURACY, "threshold_on": "plantdoc validation"}
    config["config_hash"] = hashlib.sha256(json.dumps(config, sort_keys=True).encode()
                                           ).hexdigest()[:12]
    log_path = EXPERIMENTS_DIR / "vision_recalibrate.jsonl"
    if log_path.exists() and any(r["config"].get("config_hash") == config["config_hash"]
                                 for r in read_records(log_path)):
        raise SystemExit("this recalibration was already scored; refusing to score it again")
    val = df[(df["split"] == "val") & (df["setting"] == "field")].reset_index(drop=True)
    test = df[df["split"] == "test"].reset_index(drop=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    results: dict = {}
    with track_experiment("vision_recalibrate", config, seed=None,
                          split_id="krishios-vision-v1") as rec:
        for seed in SEEDS:
            name = f"E1_all_seed{seed}.pt"
            ck = torch.load(RUNS / args.run / name, map_location="cpu", weights_only=False)
            if ck["crops"] != crops or ck["conditions"] != conds:
                raise SystemExit(f"{name}: labels differ from the dataset")
            cfg = TrainConfig(backbone=ck["backbone"], seed=seed)
            model = build_model(cfg, len(crops), len(conds))
            model.load_state_dict(ck["state_dict"])
            model = model.to(device).eval()
            dc = ck["data_config"]
            _, tf = _transforms(cfg, dc["mean"], dc["std"])
            vc, vd = predict_logits(model, DataLoader(ImageSet(val, DATA / "cache", tf),
                                                      batch_size=64,
                                                      num_workers=cfg.num_workers), device)
            yc, yd = val["crop_idx"].to_numpy(), val["cond_idx"].to_numpy()
            t_crop = vm.fit_temperature(vc, yc)
            t_cond = vm.fit_temperature(vm.conditional_condition(vd, crop_of_cond, yc), yd)
            pd_val = (val["source"] == "plantdoc").to_numpy()
            p = vm.softmax(vc[pd_val], t_crop)
            pred = p.argmax(1)
            usable = supported[pred]
            threshold = vm.confidence_threshold(p.max(1)[usable],
                                                pred[usable] == yc[pd_val][usable],
                                                TARGET_ACCURACY)
            tc, td = predict_logits(model, DataLoader(ImageSet(test, DATA / "cache", tf),
                                                      batch_size=64,
                                                      num_workers=cfg.num_workers), device)
            old = ck["temperature"]
            res: dict = {"temperature_old": old,
                         "temperature_new": {"crop": t_crop, "condition": t_cond},
                         "threshold_new": threshold, "scores": {}}
            ty = test["crop_idx"].to_numpy()
            for group, mask in {"field": test["setting"] == "field",
                                "source:plantdoc": test["source"] == "plantdoc",
                                "source:agml_rice_india": test["source"] == "agml_rice_india"
                                }.items():
                m = mask.to_numpy()
                before = evaluate(test[m], tc[m], td[m], old["crop"], old["condition"],
                                  crop_of_cond)
                after = evaluate(test[m], tc[m], td[m], t_crop, t_cond, crop_of_cond)
                res["scores"][group] = {
                    "crop_top1": after["crop"]["top1"],
                    "crop_ece_old": before["crop"]["ece"], "crop_ece_new": after["crop"]["ece"],
                    "condition_top1": after["condition_given_crop"]["top1"],
                    "condition_ece_old": before["condition_given_crop"]["ece"],
                    "condition_ece_new": after["condition_given_crop"]["ece"],
                    "app_auto_old": app_auto_accept(tc[m], ty[m], old["crop"], supported,
                                                    OLD_THRESHOLD),
                    "app_auto_new": app_auto_accept(tc[m], ty[m], t_crop, supported, threshold),
                }
            results[f"seed{seed}"] = res
            print(seed, json.dumps({"t": res["temperature_new"], "threshold": threshold}),
                  flush=True)
            del model
            torch.cuda.empty_cache()
        rec.metrics = {k: {"threshold": v["threshold_new"], **v["temperature_new"]}
                       for k, v in results.items()}
        path = REPORTS_DIR / "data" / f"vision_recalibrate_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config, "results": results},
                                   indent=1), encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
    print("run_id", rec.run_id, "\nwrote", path)


if __name__ == "__main__":
    main()
