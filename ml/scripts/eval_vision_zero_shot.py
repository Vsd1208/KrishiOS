"""Phase 9: open-weights zero-shot baseline (BioCLIP, MIT) on the vision test sets.

Replaces the brief's Gemini comparison (the user has no pay-as-you-go Gemini; nothing leaves
the machine). BioCLIP (imageomics/bioclip, ViT-B/16, trained on TreeOfLife-10M) is run locally
with no training on our labels:

- crop identification: "a photo of <scientific name>, a <common name> plant." per crop;
- condition given the true crop: "a photo of a <crop> leaf with <condition>." /
  "a photo of a healthy <crop> leaf.", among that crop's conditions only.

Scored once on the same test rows as the trained models (field and lab separately).

Usage (from ml/)::

    uv run --no-sync python scripts/eval_vision_zero_shot.py
"""

from __future__ import annotations

import json

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, REPORTS_DIR
from krishios_ml.vision import metrics as vm

DATA = DATA_DIR / "processed" / "vision" / "v1"
MODEL = "hf-hub:imageomics/bioclip"
SCIENTIFIC = {
    "apple": ("Malus domestica", "apple"), "blueberry": ("Vaccinium corymbosum", "blueberry"),
    "cherry": ("Prunus avium", "cherry"), "maize": ("Zea mays", "maize"),
    "grapes": ("Vitis vinifera", "grape"), "citrus": ("Citrus sinensis", "orange"),
    "peach": ("Prunus persica", "peach"), "bell_pepper": ("Capsicum annuum", "bell pepper"),
    "potato": ("Solanum tuberosum", "potato"), "raspberry": ("Rubus idaeus", "raspberry"),
    "soybean": ("Glycine max", "soybean"), "squash": ("Cucurbita pepo", "squash"),
    "strawberry": ("Fragaria ananassa", "strawberry"),
    "tomato": ("Solanum lycopersicum", "tomato"), "paddy": ("Oryza sativa", "rice"),
}


def main() -> None:
    import open_clip
    import torch
    from PIL import Image

    df = pd.read_parquet(DATA / "images.parquet")
    test = df[(df["split"] == "test") & (df["crop_label"].isin(SCIENTIFIC))].reset_index(
        drop=True)
    crops = sorted(test["crop_label"].unique())
    config = {"model": MODEL, "crops": crops, "rows": len(test),
              "excluded": "no_plant (background) rows: no species to name"}
    with track_experiment("vision_zero_shot", config, seed=None,
                          split_id="krishios-vision-v1") as rec:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model, _, preprocess = open_clip.create_model_and_transforms(MODEL)
        tok = open_clip.get_tokenizer(MODEL)
        model = model.to(device).eval()

        def text_features(prompts: list[str]) -> torch.Tensor:
            with torch.no_grad():
                f = model.encode_text(tok(prompts).to(device))
            return f / f.norm(dim=-1, keepdim=True)

        crop_text = text_features([f"a photo of {SCIENTIFIC[c][0]}, a {SCIENTIFIC[c][1]} plant."
                                   for c in crops])
        feats = []
        with torch.no_grad():
            for i in range(0, len(test), 64):
                batch = torch.stack([preprocess(Image.open(DATA / "cache" / p).convert("RGB"))
                                     for p in test["cache"].iloc[i:i + 64]]).to(device)
                f = model.encode_image(batch)
                feats.append((f / f.norm(dim=-1, keepdim=True)).float().cpu())
        img = torch.cat(feats)
        scale = float(model.logit_scale.exp())
        crop_logits = (scale * img @ crop_text.float().cpu().T).numpy()
        yc = test["crop_label"].map({c: i for i, c in enumerate(crops)}).to_numpy()
        # Condition given the true crop: prompts among that crop's conditions only.
        cond_pred, cond_true = np.empty(len(test), dtype=object), test["condition"].to_numpy()
        for crop in crops:
            m = (test["crop_label"] == crop).to_numpy()
            options = sorted(df.loc[df["crop_label"] == crop, "condition"].unique())
            common = SCIENTIFIC[crop][1]
            prompts = [f"a photo of a healthy {common} leaf." if o == "healthy"
                       else f"a photo of a {common} leaf with {o.replace('_', ' ')}."
                       for o in options]
            t = text_features(prompts).float().cpu()
            cond_pred[m] = np.array(options)[(img[m] @ t.T).argmax(1).numpy()]
        out = {}
        for setting in ("field", "lab"):
            m = (test["setting"] == setting).to_numpy()
            if not m.any():
                continue
            labels = np.unique(cond_true[m])
            idx = {c: i for i, c in enumerate(labels)}
            out[setting] = {
                "crop": vm.summary(crop_logits[m], yc[m]),
                "condition_given_crop": {
                    "n": int(m.sum()),
                    "top1": float((cond_pred[m] == cond_true[m]).mean()),
                    "macro_f1": vm.macro_f1(np.array([idx.get(c, -1) for c in cond_pred[m]]),
                                            np.array([idx[c] for c in cond_true[m]])),
                },
            }
        rec.metrics = out
        path = REPORTS_DIR / "data" / f"vision_zero_shot_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config, "metrics": out},
                                   indent=1), encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
    print(json.dumps(out, indent=1), "\nrun_id", rec.run_id)


if __name__ == "__main__":
    main()
