"""Phase 9: export a trained crop/condition checkpoint to ONNX for CPU serving.

Writes ``ml/artifacts/vision/<version>/{model.onnx, labels.json}`` (git-ignored), which the
backend ``onnx-crop-classifier`` provider loads. The export is checked for parity: ONNX Runtime
(CPU) logits must match PyTorch on real cached images within ``ATOL``.

``labels.json`` carries everything the provider needs: crop labels with their catalog key and
whether the catalog marks them vision-supported, condition labels with display names, the
validation temperatures, preprocessing (mean/std/size), the licence and the evidence run ids.

Usage (from ml/)::

    uv run --no-sync python scripts/export_vision_onnx.py --run <train_run_id> \\
        --checkpoint E1_all_seed0.pt
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, ML_ROOT

RUNS = ML_ROOT / "artifacts" / "vision" / "runs"
OUT = ML_ROOT / "artifacts" / "vision"
DATA = DATA_DIR / "processed" / "vision" / "v1"
CATALOG = ML_ROOT / "reference" / "crop_catalog.csv"
ATOL = 1e-3
LICENSE = ("Weights trained on PlantVillage (treated as CC BY-SA 3.0, the paper's licence), "
           "PlantDoc (CC BY 4.0) and Rice Leaf Disease Image Samples (CC BY 4.0); "
           "distribute under CC BY-SA 3.0 with attribution.")


def display(condition: str) -> str:
    return condition.replace("_", " ")


def main() -> None:
    import onnxruntime as ort
    import torch

    from krishios_ml.vision.train import TrainConfig, _transforms, build_model

    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--supported", nargs="*", default=None,
                    help="catalog crops to mark supported (default: every catalog crop the "
                         "model was trained on)")
    ap.add_argument("--calibration", default=None,
                    help="vision_recalibrate_<run>.json: use its field-fitted values for this "
                         "checkpoint's seed")
    args = ap.parse_args()
    ck = torch.load(RUNS / args.run / args.checkpoint, map_location="cpu", weights_only=False)
    crops, conds, dc = ck["crops"], ck["conditions"], ck["data_config"]
    temperature, threshold, calibration_run = ck["temperature"], None, None
    if args.calibration:
        cal = json.loads(Path(args.calibration).read_text(encoding="utf-8"))
        if cal["config"]["train_run"] != args.run:
            raise SystemExit("the calibration file belongs to another training run")
        seed = args.checkpoint.rsplit("seed", 1)[1].split(".")[0]
        entry = cal["results"][f"seed{seed}"]
        temperature, threshold = entry["temperature_new"], entry["threshold_new"]
        calibration_run = cal["run_id"]
    cfg = TrainConfig(backbone=ck["backbone"])
    model = build_model(cfg, len(crops), len(conds))
    model.load_state_dict(ck["state_dict"])
    model.eval()
    keys = set(pd.read_csv(CATALOG, keep_default_na=False)["crop_canonical"])
    supported = set(args.supported) if args.supported is not None else (set(crops) & keys)
    exported = datetime.now(UTC)
    version = f"vision-{args.run}-{exported:%Y%m%d%H%M}"
    dest = OUT / version
    dest.mkdir(parents=True, exist_ok=True)
    with track_experiment("vision_export", {"run": args.run, "checkpoint": args.checkpoint,
                                            "version": version}, seed=None,
                          split_id="krishios-vision-v1") as rec:
        x = torch.zeros(1, 3, dc["image_size"], dc["image_size"])
        torch.onnx.export(model, x, dest / "model.onnx", input_names=["image"],
                          output_names=["crop_logits", "cond_logits"],
                          dynamic_axes={"image": {0: "batch"}}, opset_version=17)
        # Parity on real cached test images.
        from PIL import Image

        _, tf = _transforms(cfg, dc["mean"], dc["std"])
        df = pd.read_parquet(DATA / "images.parquet")
        sample = df[df["split"] == "test"].sample(min(32, len(df)), random_state=0)
        batch = torch.stack([tf(Image.open(DATA / "cache" / p).convert("RGB"))
                             for p in sample["cache"]])
        with torch.no_grad():
            t_crop, t_cond = (a.numpy() for a in model(batch))
        sess = ort.InferenceSession(str(dest / "model.onnx"), providers=["CPUExecutionProvider"])
        o_crop, o_cond = sess.run(["crop_logits", "cond_logits"], {"image": batch.numpy()})
        diff = float(max(np.abs(o_crop - t_crop).max(), np.abs(o_cond - t_cond).max()))
        if diff > ATOL:
            raise SystemExit(f"ONNX parity failed: max |diff| = {diff}")
        labels = {
            "model_name": f"krishios-vision-{ck['backbone'].split('.')[0]}",
            "model_version": version, "exported_at": exported.isoformat(),
            "image_size": dc["image_size"], "mean": dc["mean"], "std": dc["std"],
            "temperature": temperature, "confirm_threshold": threshold,
            "crops": [{"label": c, "crop_canonical": c if c in keys else None,
                       "supported": c in supported} for c in crops],
            "conditions": [{"label": c, "crop": c.split("|")[0],
                            "name": display(c.split("|")[1]),
                            "healthy": c.endswith("|healthy")} for c in conds],
            "license": LICENSE,
            "evidence": {"train_run": args.run, "checkpoint": args.checkpoint,
                         "export_run": rec.run_id, "onnx_parity_max_abs_diff": diff,
                         "calibration_run": calibration_run},
        }
        (dest / "labels.json").write_text(json.dumps(labels, indent=1), encoding="utf-8")
        rec.metrics = {"parity_max_abs_diff": diff, "crops": len(crops),
                       "conditions": len(conds), "supported": sorted(supported),
                       "onnx_mb": round(sum(f.stat().st_size for f in dest.glob("model.onnx*"))
                                        / 1e6, 2)}
        rec.artifact_path = str(dest.relative_to(ML_ROOT))
    print(json.dumps(rec.metrics, indent=1), "\nwrote", dest)


if __name__ == "__main__":
    main()
