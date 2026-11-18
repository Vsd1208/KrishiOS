"""Two-head crop + condition classifier on a compact timm backbone (Phase 9).

- Backbone: a small ImageNet-pretrained timm model (default ``efficientnet_b0``) so it trains
  on a 4 GB laptop GPU (AMP, batch 64) and runs on CPU via ONNX.
- Heads: ``crop`` (what crop is in the photo) and ``condition`` (flat ``crop|condition``
  labels, e.g. ``tomato|early_blight``, ``paddy|healthy``). At inference the condition is read
  among the predicted (or farmer-confirmed) crop's labels only.
- Sampling: each source (PlantVillage lab, PlantDoc, Paddy Doctor field) gets equal mass per
  epoch, so 54k lab images do not drown the field photos.
- Model selection: best validation epoch by the mean of crop accuracy and condition macro-F1
  over **field** validation images. Temperatures for calibration are fitted on validation.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class TrainConfig:
    backbone: str = "efficientnet_b0.ra_in1k"
    epochs: int = 8
    batch_size: int = 64
    lr: float = 6e-4
    weight_decay: float = 0.05
    label_smoothing: float = 0.1
    image_size: int = 224
    seed: int = 0
    num_workers: int = 4
    train_sources: tuple[str, ...] = ("plantvillage", "plantdoc", "paddy_doctor")
    extra: dict = field(default_factory=dict)


def _transforms(cfg: TrainConfig, mean, std):
    from torchvision import transforms as T  # noqa: N812 - torchvision convention

    train = T.Compose([
        T.RandomResizedCrop(cfg.image_size, scale=(0.55, 1.0)),
        T.RandomHorizontalFlip(),
        T.RandomRotation(15),
        T.ColorJitter(0.25, 0.25, 0.2, 0.02),
        T.ToTensor(), T.Normalize(mean, std),
    ])
    evalt = T.Compose([T.Resize(256), T.CenterCrop(cfg.image_size), T.ToTensor(),
                       T.Normalize(mean, std)])
    return train, evalt


class ImageSet:
    def __init__(self, rows: pd.DataFrame, cache_dir: Path, tf) -> None:
        self.paths = [cache_dir / p for p in rows["cache"]]
        self.crop = rows["crop_idx"].to_numpy()
        self.cond = rows["cond_idx"].to_numpy()
        self.tf = tf

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, i):
        from PIL import Image

        img = Image.open(self.paths[i]).convert("RGB")
        return self.tf(img), int(self.crop[i]), int(self.cond[i])


def build_model(cfg: TrainConfig, n_crop: int, n_cond: int):
    import timm
    import torch.nn as nn

    class TwoHead(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.backbone = timm.create_model(cfg.backbone, pretrained=True, num_classes=0)
            d = self.backbone.num_features
            self.crop = nn.Linear(d, n_crop)
            self.cond = nn.Linear(d, n_cond)

        def forward(self, x):
            f = self.backbone(x)
            return self.crop(f), self.cond(f)

    return TwoHead()


@dataclass
class Fitted:
    model: object
    history: list[dict]
    best_epoch: int
    seconds: float
    data_config: dict


def predict_logits(model, loader, device) -> tuple[np.ndarray, np.ndarray]:
    import torch

    model.eval()
    crops, conds = [], []
    with torch.no_grad(), torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
        for x, _, _ in loader:
            a, b = model(x.to(device, non_blocking=True))
            crops.append(a.float().cpu().numpy())
            conds.append(b.float().cpu().numpy())
    return np.concatenate(crops), np.concatenate(conds)


def fit(cfg: TrainConfig, train: pd.DataFrame, val: pd.DataFrame, cache_dir: Path,
        n_crop: int, n_cond: int, score_fn, log=print) -> Fitted:
    """``score_fn(val_rows, crop_logits, cond_logits) -> float`` picks the best epoch."""
    import timm
    import torch
    from torch.utils.data import DataLoader, WeightedRandomSampler

    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model(cfg, n_crop, n_cond).to(device)
    dc = timm.data.resolve_data_config({}, model=model.backbone)
    tf_train, tf_eval = _transforms(cfg, dc["mean"], dc["std"])
    train = train[train["source"].isin(cfg.train_sources)].reset_index(drop=True)
    counts = train["source"].map(train["source"].value_counts())
    sampler = WeightedRandomSampler(torch.tensor((1.0 / counts).to_numpy()), len(train),
                                    replacement=True,
                                    generator=torch.Generator().manual_seed(cfg.seed))
    dl_train = DataLoader(ImageSet(train, cache_dir, tf_train), batch_size=cfg.batch_size,
                          sampler=sampler, num_workers=cfg.num_workers, pin_memory=True,
                          persistent_workers=cfg.num_workers > 0,
                          drop_last=len(train) > cfg.batch_size)
    dl_val = DataLoader(ImageSet(val, cache_dir, tf_eval), batch_size=cfg.batch_size * 2,
                        num_workers=cfg.num_workers, pin_memory=True)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    steps = max(1, cfg.epochs * len(dl_train))
    warm = max(1, len(dl_train) // 2)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / warm) * 0.5 * (1 + math.cos(math.pi * min(s, steps)
                                                                        / steps)))
    scaler = torch.amp.GradScaler(enabled=device.type == "cuda")
    ce = torch.nn.CrossEntropyLoss(label_smoothing=cfg.label_smoothing)
    history, best, best_state, t0 = [], -1.0, None, time.time()
    for epoch in range(cfg.epochs):
        model.train()
        total, n = 0.0, 0
        for x, yc, yd in dl_train:
            x, yc, yd = (t.to(device, non_blocking=True) for t in (x, yc, yd))
            with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
                a, b = model(x)
                loss = ce(a, yc) + ce(b, yd)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
            total += float(loss.detach()) * len(x)
            n += len(x)
        crop_l, cond_l = predict_logits(model, dl_val, device)
        score = float(score_fn(val, crop_l, cond_l))
        history.append({"epoch": epoch, "train_loss": total / max(n, 1), "val_score": score,
                        "seconds": round(time.time() - t0, 1)})
        log(f"epoch {epoch}: loss {total / max(n, 1):.4f} val {score:.4f}")
        if score > best:
            best = score
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            best_epoch = epoch
    model.load_state_dict(best_state)
    return Fitted(model, history, best_epoch, time.time() - t0,
                  {"mean": list(dc["mean"]), "std": list(dc["std"]),
                   "image_size": cfg.image_size})
