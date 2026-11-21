"""Independent test of the served vision model on Indian field photos it has never seen.

Uses the photos from ``download_india_vision.py`` after ``check_india_vision.py``: one photo per
near-copy group, none close to a training image, and photos filed under two labels dropped.
Preprocessing copies the backend provider (EXIF upright, shorter side 256, centre 224 crop,
calibrated temperatures, the artifact's confirmation threshold).

Three questions:
1. Crop recognition on crops the model knows (potato, soybean, tomato).
2. Crops the model does not know (chilli, wheat): how often is one auto-accepted as a supported
   crop? That is the harmful case, because the farmer would not be asked.
3. Disease reading with the crop confirmed, where the photo's label maps to a model class.

``--split test`` scores only the held-out test photos of ``prepare_india_vision.py`` (the
photos a retrained model is tested on), so the served model and a retrained one are compared on
the same photos.

Usage (from ml/)::

    uv run --no-sync python scripts/eval_vision_india.py [--split test] [--artifact <version>]
"""

from __future__ import annotations

import json
import math
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
from PIL import Image, ImageOps

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import ARTIFACTS_DIR, DATA_DIR, ML_ROOT, REPORTS_DIR

ROOT = DATA_DIR / "raw" / "vision" / "india"
SERVED = "vision-560b033f785d-202611180856"  # the Phase 9 model
FIELD_CROPS = ("chilli", "potato", "soybean", "tomato", "wheat")  # crops in these photos
Image.MAX_IMAGE_PIXELS = 80_000_000
# photo label -> model condition (only where the model has the same disease)
CONDITION_MAP = {
    "potato/early_blight": "potato|early_blight",
    "potato/late_blight": "potato|late_blight",
    "potato/healthy": "potato|healthy",
    "tomato/Alternaria": "tomato|early_blight",  # Alternaria solani causes early blight
}


def softmax(z: np.ndarray, t: float) -> np.ndarray:
    z = z / t
    e = np.exp(z - z.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def tensor(path, labels: dict) -> np.ndarray:
    size = int(labels["image_size"])
    with Image.open(path) as im:
        im.draft("RGB", (512, 512))  # JPEG decodes at >= 512 px; then the provider's resizing
        img = ImageOps.exif_transpose(im).convert("RGB")
    w, h = img.size
    scale = 256 / min(w, h)
    img = img.resize((max(size, round(w * scale)), max(size, round(h * scale))), Image.BICUBIC)
    w, h = img.size
    left, top = (w - size) // 2, (h - size) // 2
    x = np.asarray(img.crop((left, top, left + size, top + size)), dtype=np.float32) / 255.0
    x = (x - np.array(labels["mean"], dtype=np.float32)) / np.array(labels["std"],
                                                                    dtype=np.float32)
    return x.transpose(2, 0, 1)


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    if n == 0:
        return [math.nan, math.nan]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - r, 4), round(c + r, 4)]


def rate(k: int, n: int) -> dict:
    return {"n": n, "k": k, "rate": round(k / n, 4) if n else None, "ci95": wilson(k, n)}


def main() -> None:
    import argparse

    import onnxruntime as ort

    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["all", "test"], default="all")
    ap.add_argument("--artifact", default=SERVED, help="model version under artifacts/vision")
    args = ap.parse_args()
    artifact = ARTIFACTS_DIR / "vision" / args.artifact

    labels = json.loads((artifact / "labels.json").read_text(encoding="utf-8"))
    crops, conds = labels["crops"], labels["conditions"]
    crop_names = np.array([c["label"] for c in crops])
    supported = np.array([c["supported"] for c in crops])
    cond_names = np.array([c["label"] for c in conds])
    cond_crop = np.array([c["crop"] for c in conds])
    threshold = labels["confirm_threshold"]
    cut = np.inf if threshold is None else threshold  # null: never auto-accept, like the backend
    temps = labels["temperature"]
    known_crops = sorted(set(FIELD_CROPS) & set(crop_names))  # crops this model was taught
    unknown_crops = sorted(set(FIELD_CROPS) - set(known_crops))
    label_map = pd.read_csv(ML_ROOT / "reference" / "vision_label_map.csv", keep_default_na=False)
    label_map = label_map[(label_map["source"] == "india_field") & (label_map["crop_label"] != "")]
    label_target = dict(zip(label_map["raw_class"],
                            label_map["crop_label"] + "|" + label_map["condition"], strict=True))

    files = pd.read_parquet(ROOT / "quality_files.parquet")
    quality = json.loads((ROOT / "quality.json").read_text(encoding="utf-8"))
    conflicted = {h for h in quality["exact_label_conflicts"]}
    if args.split == "test":  # exactly the retraining run's Indian test rows
        held = pd.read_parquet(DATA_DIR / "processed" / "vision" / "india_v1" / "images.parquet")
        test = set(held.loc[held["split"] == "test", "member"])
        files = files.drop_duplicates("sha256")
        files = files[files["file"].isin(test)]
    else:
        files = files[~files["near_train"] & ~files["group"].duplicated(keep="first")]
    files = files[~files["sha256"].str[:12].isin(conflicted)].reset_index(drop=True)
    files["crop"] = files["label"].str.split("/").str[0]

    session = ort.InferenceSession(str(artifact / "model.onnx"),
                                   providers=["CPUExecutionProvider"])
    config = {"artifact": labels["model_version"], "photos": len(files),
              "threshold": threshold, "dedup": "fine dhash <= 20/256, one per group",
              "condition_map": CONDITION_MAP, "split": args.split}
    with track_experiment("vision_india_field_test", config, seed=None,
                          split_id="india-mendeley-v1") as rec:
        with ThreadPoolExecutor(6) as pool:
            xs = list(pool.map(lambda p: tensor(ROOT / p, labels), files["file"]))
        crop_logits, cond_logits = [], []
        for i in range(0, len(xs), 32):
            a, b = session.run(["crop_logits", "cond_logits"],
                               {"image": np.stack(xs[i:i + 32]).astype(np.float32)})
            crop_logits.append(a)
            cond_logits.append(b)
        pc = softmax(np.concatenate(crop_logits), temps["crop"])
        cl = np.concatenate(cond_logits)
        top = pc.argmax(1)
        files["pred_crop"] = crop_names[top]
        files["crop_conf"] = pc.max(1)
        files["auto_accepted"] = supported[top] & (files["crop_conf"] >= cut)

        out: dict = {"photos_by_label": dict(Counter(files["label"]))}
        # 1. crop recognition where the model knows the crop
        crop_rows = {}
        for crop in known_crops:
            s = files[files["crop"] == crop]
            ok = s["pred_crop"] == crop
            sure = s["crop_conf"] >= cut  # what auto-accept would do if the crop were enabled
            crop_rows[crop] = {**rate(int(ok.sum()), len(s)),
                               "predicted": dict(Counter(s["pred_crop"]).most_common(4)),
                               "auto_accepted": rate(int(s["auto_accepted"].sum()), len(s)),
                               "wrong_and_auto_accepted": int((~ok & s["auto_accepted"]).sum()),
                               "if_enabled": {"share": rate(int(sure.sum()), len(s)),
                                              "accuracy": rate(int((ok & sure).sum()),
                                                               int(sure.sum()))}}
        out["crop_recognition"] = crop_rows
        # 2. crops the model does not know
        unknown = {}
        for crop in unknown_crops:
            s = files[files["crop"] == crop]
            unknown[crop] = {"auto_accepted_as_supported": rate(int(s["auto_accepted"].sum()),
                                                                len(s)),
                             "predicted": dict(Counter(s["pred_crop"]).most_common(5)),
                             "median_top_conf": round(float(s["crop_conf"].median()), 4)}
        out["unknown_crops"] = unknown
        # 3. disease with the crop confirmed by the farmer
        disease = {}
        for label, target in CONDITION_MAP.items():
            s = files.index[files["label"] == label]
            crop = target.split("|")[0]
            mask = cond_crop == crop
            p = softmax(np.where(mask, cl[s], -np.inf), temps["condition"])
            pred = cond_names[p.argmax(1)]
            disease[label] = {**rate(int((pred == target).sum()), len(s)),
                              "predicted": dict(Counter(pred).most_common(4)),
                              "mean_conf": round(float(p.max(1).mean()), 4)}
        potato = [disease[k] for k in CONDITION_MAP if k.startswith("potato")]
        disease["potato_balanced_accuracy"] = round(float(np.mean([d["rate"] for d in potato])),
                                                    4)
        out["disease_with_confirmed_crop"] = disease
        # every photo label whose condition this model has a class for (label map targets)
        by_label, by_crop = {}, {}
        for label, target in sorted(label_target.items()):
            s = files.index[files["label"] == label]
            if target not in set(cond_names) or len(s) == 0:
                continue
            crop = target.split("|")[0]
            p = softmax(np.where(cond_crop == crop, cl[s], -np.inf), temps["condition"])
            pred = cond_names[p.argmax(1)]
            by_label[label] = {**rate(int((pred == target).sum()), len(s)), "target": target,
                               "predicted": dict(Counter(pred).most_common(3))}
            by_crop.setdefault(crop, []).append(by_label[label]["rate"])
        out["disease_all_labels"] = {
            "by_label": by_label,
            "balanced_accuracy_by_crop": {c: round(float(np.mean(v)), 4)
                                          for c, v in sorted(by_crop.items())}}
        # tomato photos whose problem the model has no class for (pests, disorder)
        other = files.index[files["label"].isin(["tomato/Leaf miner", "tomato/Insect attack",
                                                 "tomato/Physiological disorder",
                                                 "tomato/Alternaria+Leafminer"])]
        mask = cond_crop == "tomato"
        p = softmax(np.where(mask, cl[other], -np.inf), temps["condition"])
        out["tomato_unmodelled_problems"] = {
            "n": len(other), "predicted": dict(Counter(cond_names[p.argmax(1)]).most_common(5)),
            "mean_conf": round(float(p.max(1).mean()), 4)}
        rec.metrics = {"crop_recognition": {k: v["rate"] for k, v in crop_rows.items()},
                       "unknown_auto_accepted": {k: v["auto_accepted_as_supported"]["rate"]
                                                 for k, v in unknown.items()},
                       "potato_balanced_accuracy": disease["potato_balanced_accuracy"],
                       "tomato_alternaria": disease["tomato/Alternaria"]["rate"],
                       "disease_balanced_by_crop":
                           out["disease_all_labels"]["balanced_accuracy_by_crop"]}
        path = REPORTS_DIR / "data" / f"vision_india_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config, **out}, indent=1),
                        encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
        # condition read with the true crop confirmed (for later checks, e.g. photo-size shortcuts)
        pred_cond = np.full(len(files), "", dtype=object)
        for crop in known_crops:
            s = files.index[files["crop"] == crop]
            p = softmax(np.where(cond_crop == crop, cl[s], -np.inf), temps["condition"])
            pred_cond[s] = cond_names[p.argmax(1)]
        files["pred_cond"] = pred_cond
        cols = ["sha256", "label", "pred_crop", "crop_conf", "auto_accepted", "pred_cond"]
        files[cols].to_parquet(
            ROOT / f"predictions_{rec.run_id}.parquet", index=False)
    print(json.dumps(out, indent=1))
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
