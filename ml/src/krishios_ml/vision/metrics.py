"""Vision metrics: top-1 / top-5 accuracy, macro-F1, expected calibration error, and
temperature scaling fitted on validation logits (Phase 9)."""

from __future__ import annotations

from itertools import pairwise

import numpy as np


def softmax(z: np.ndarray, t: float = 1.0) -> np.ndarray:
    z = z / t
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def topk(probs: np.ndarray, y: np.ndarray, k: int) -> float:
    k = min(k, probs.shape[1])
    idx = np.argpartition(-probs, k - 1, axis=1)[:, :k]
    return float((idx == y[:, None]).any(axis=1).mean())


def macro_f1(pred: np.ndarray, y: np.ndarray, labels: np.ndarray | None = None) -> float:
    """Macro-F1 over the classes present in ``y`` (classes absent from the gold labels are
    not averaged, so a test set with fewer classes is not penalised for them)."""
    labels = np.unique(y) if labels is None else labels
    f1s = []
    for c in labels:
        tp = np.sum((pred == c) & (y == c))
        fp = np.sum((pred == c) & (y != c))
        fn = np.sum((pred != c) & (y == c))
        f1s.append(0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn))
    return float(np.mean(f1s)) if f1s else float("nan")


def ece(probs: np.ndarray, y: np.ndarray, bins: int = 15) -> float:
    conf = probs.max(axis=1)
    correct = probs.argmax(axis=1) == y
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for lo, hi in pairwise(edges):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            total += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(total)


def fit_temperature(logits: np.ndarray, y: np.ndarray) -> float:
    """1-D search for the temperature minimising validation NLL."""
    best_t, best_nll = 1.0, np.inf
    for t in np.exp(np.linspace(np.log(0.3), np.log(5.0), 120)):
        p = softmax(logits, t)
        nll = -np.mean(np.log(np.clip(p[np.arange(len(y)), y], 1e-12, None)))
        if nll < best_nll:
            best_t, best_nll = float(t), nll
    return best_t


def confidence_threshold(conf: np.ndarray, correct: np.ndarray, target: float = 0.95,
                         min_rows: int = 30) -> float | None:
    """Lowest threshold (0.50 to 0.99) at which the rows at or above it are at least ``target``
    accurate, with at least ``min_rows`` of them. None if no threshold qualifies."""
    for t in np.round(np.arange(0.50, 0.995, 0.01), 2):
        m = conf >= t
        if m.sum() >= min_rows and correct[m].mean() >= target:
            return float(t)
    return None


def summary(logits: np.ndarray, y: np.ndarray, t: float = 1.0) -> dict[str, float]:
    p = softmax(logits, t)
    pred = p.argmax(axis=1)
    return {"n": len(y), "top1": float((pred == y).mean()), "top5": topk(p, y, 5),
            "macro_f1": macro_f1(pred, y), "ece": ece(p, y)}


def conditional_condition(cond_logits: np.ndarray, crop_of_cond: np.ndarray,
                          crop: np.ndarray) -> np.ndarray:
    """Condition logits restricted to each row's crop (predicted or farmer-confirmed); other
    crops' conditions get -inf."""
    mask = crop_of_cond[None, :] == crop[:, None]
    return np.where(mask, cond_logits, -np.inf)
