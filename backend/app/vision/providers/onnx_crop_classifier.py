"""Local crop identification + disease model (ONNX on CPU). Phase 9.

Artifact (exported by ``ml/scripts/export_vision_onnx.py``)::

    <ML_ARTIFACTS_DIR>/vision/<version>/model.onnx     outputs: crop_logits, cond_logits
    <ML_ARTIFACTS_DIR>/vision/<version>/labels.json    labels, temperatures, preprocessing

Images never leave the machine. Probabilities are temperature-calibrated on validation. The
condition is read only among the conditions of the crop in the photo: the farmer-confirmed
crop when the caller passes ``metadata["confirmed_crop"]``, else the predicted crop.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from app.vision.providers.base import Condition, Observation, VisionResult

MIN_CONDITION_PROB = 0.01  # conditions below this are not listed
NEVER_AUTO_ACCEPT = 1.01  # above any probability


def latest_vision_artifact(root: Path, version: str | None = None) -> Path | None:
    if version:
        d = root / version
        return d if (d / "labels.json").exists() else None
    dirs = [d for d in root.glob("*") if (d / "labels.json").exists()] if root.exists() else []
    if not dirs:
        return None
    return max(dirs, key=lambda d: json.loads((d / "labels.json").read_text())["exported_at"])


def resolve_threshold(labels: dict[str, Any], default: float) -> float:
    """The threshold validated with the artifact wins over the setting. An artifact where no
    threshold reached the accuracy target (null) never auto-accepts: the farmer is always asked."""
    if "confirm_threshold" not in labels:
        return default
    value = labels["confirm_threshold"]
    return NEVER_AUTO_ACCEPT if value is None else float(value)


def _softmax(z: np.ndarray, t: float) -> np.ndarray:
    z = z / t
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


class OnnxCropClassifier:
    def __init__(self, artifact: Path, confirm_threshold: float = 0.6) -> None:
        import onnxruntime as ort  # noqa: PLC0415 - optional local-ml dependency

        self._labels: dict[str, Any] = json.loads((artifact / "labels.json").read_text(
            encoding="utf-8"))
        self._session = ort.InferenceSession(str(artifact / "model.onnx"),
                                             providers=["CPUExecutionProvider"])
        self._threshold = resolve_threshold(self._labels, confirm_threshold)
        self._crops = self._labels["crops"]
        self._conds = self._labels["conditions"]
        self._crop_of_cond = np.array([c["crop"] for c in self._conds])

    @property
    def model_name(self) -> str:
        return self._labels["model_name"]

    @property
    def model_version(self) -> str:
        return self._labels["model_version"]

    def _tensor(self, image_path: Path) -> np.ndarray:
        from PIL import Image, ImageOps  # noqa: PLC0415

        size = int(self._labels["image_size"])
        # Phones store rotation in EXIF; the model must see the photo upright.
        img = ImageOps.exif_transpose(Image.open(image_path)).convert("RGB")
        w, h = img.size
        scale = 256 / min(w, h)
        img = img.resize((max(size, round(w * scale)), max(size, round(h * scale))),
                         Image.BICUBIC)
        w, h = img.size
        left, top = (w - size) // 2, (h - size) // 2
        img = img.crop((left, top, left + size, top + size))
        x = np.asarray(img, dtype=np.float32) / 255.0
        x = (x - np.array(self._labels["mean"], dtype=np.float32)) / np.array(
            self._labels["std"], dtype=np.float32)
        return x.transpose(2, 0, 1)[None]

    def _key(self, crop: dict[str, Any]) -> str:
        return crop["crop_canonical"] or f"other:{crop['label']}"

    def classify(self, image_path: Path, confirmed_crop: str | None = None) -> VisionResult:
        t0 = time.perf_counter()
        crop_logits, cond_logits = self._session.run(
            ["crop_logits", "cond_logits"], {"image": self._tensor(image_path)})
        temps = self._labels["temperature"]
        p_crop = _softmax(crop_logits[0], temps["crop"])
        order = np.argsort(-p_crop)
        candidates = [(self._key(self._crops[i]), round(float(p_crop[i]), 4))
                      for i in order[:3]]
        top = self._crops[order[0]]
        supported = bool(top["supported"]) and float(p_crop[order[0]]) >= self._threshold
        crop_label = top["label"]
        if confirmed_crop:  # farmer-confirmed crop wins (condition read among its classes)
            match = [c for c in self._crops if c["crop_canonical"] == confirmed_crop]
            crop_label = match[0]["label"] if match else None
        conditions: list[Condition] = []
        observations: list[Observation] = []
        if crop_label is not None and (self._crop_of_cond == crop_label).any():
            mask = self._crop_of_cond == crop_label
            p = _softmax(np.where(mask, cond_logits[0], -np.inf), temps["condition"])
            for i in np.argsort(-p)[:3]:
                if not mask[i] or p[i] < MIN_CONDITION_PROB:
                    continue
                c = self._conds[i]
                conditions.append(Condition(name=c["name"], confidence=round(float(p[i]), 4)))
            best = conditions[0] if conditions else None
            if best is not None and self._conds[int(np.argmax(p))]["healthy"]:
                observations.append(Observation("no visible disease symptoms", best.confidence))
        detected = (confirmed_crop or top["crop_canonical"]) if (confirmed_crop or supported) \
            else None
        return VisionResult(
            crop_detected=detected, observations=observations, candidate_conditions=conditions,
            model_name=self.model_name, model_version=self.model_version,
            inference_ms=round((time.perf_counter() - t0) * 1000, 1),
            metadata={"crop_label": crop_label, "license": self._labels.get("license")},
            crop_candidates=candidates, crop_supported=supported or bool(confirmed_crop),
        )

    async def analyze(self, image_path: Path, metadata: dict) -> VisionResult:
        import asyncio  # noqa: PLC0415

        return await asyncio.to_thread(self.classify, image_path,
                                       (metadata or {}).get("confirmed_crop"))

    async def health(self) -> bool:
        return self._session is not None
