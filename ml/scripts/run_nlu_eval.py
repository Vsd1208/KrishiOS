"""NLU evaluation on ml/evaluation_sets/nlu/utterances_v1.jsonl (labels: DRAFT, pending review).

Metrics: intent accuracy and macro-F1, per-segment intent accuracy (en, te, hi, te-cs, hi-cs),
language-ID accuracy, code-switch accuracy, and slot precision/recall/F1 for crop (catalog
key) and district (LGD name). Slot scoring counts a predicted value as correct only if it
equals the gold value; predicting a value where gold is null is a false positive.

Usage (from backend/)::

    uv run python ../ml/scripts/run_nlu_eval.py --providers rule-based-nlu gemini-nlu
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import Counter

import _bootstrap  # noqa: F401

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import ML_ROOT, REPORTS_DIR

DATA = ML_ROOT / "evaluation_sets" / "nlu" / "utterances_v1.jsonl"


def segment(row: dict) -> str:
    return f"{row['language']}-cs" if row["code_switched"] and row["language"] != "en" \
        else row["language"]


def slot_prf(gold: list, pred: list) -> dict:
    tp = sum(1 for g, p in zip(gold, pred, strict=True) if g is not None and p == g)
    fp = sum(1 for g, p in zip(gold, pred, strict=True) if p is not None and p != g)
    fn = sum(1 for g, p in zip(gold, pred, strict=True) if g is not None and p != g)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4),
            "tp": tp, "fp": fp, "fn": fn}


def macro_f1(gold: list[str], pred: list[str]) -> float:
    labels = sorted(set(gold))
    f1s = []
    for lab in labels:
        tp = sum(g == lab and p == lab for g, p in zip(gold, pred, strict=True))
        fp = sum(g != lab and p == lab for g, p in zip(gold, pred, strict=True))
        fn = sum(g == lab and p != lab for g, p in zip(gold, pred, strict=True))
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return round(sum(f1s) / len(f1s), 4)


async def run(provider_name: str, rows: list[dict]) -> dict:
    from app.nlu.selection import nlu_selector

    provider = nlu_selector.get(provider_name)
    preds, latencies, errors = [], [], 0
    for row in rows:
        t0 = time.perf_counter()
        try:
            preds.append(await provider.parse(row["text"]))
        except Exception:  # count as wrong, keep going
            preds.append(None)
            errors += 1
        latencies.append((time.perf_counter() - t0) * 1000)

    gold_int = [r["intent"] for r in rows]
    pred_int = [p.intent.value if p else "error" for p in preds]
    seg_acc: dict[str, list[int]] = {}
    for r, g, p in zip(rows, gold_int, pred_int, strict=True):
        seg_acc.setdefault(segment(r), []).append(int(g == p))
    confusions = Counter((g, p) for g, p in zip(gold_int, pred_int, strict=True) if g != p)
    return {
        "n": len(rows),
        "errors": errors,
        "intent_accuracy": round(sum(g == p for g, p in zip(gold_int, pred_int, strict=True))
                                 / len(rows), 4),
        "intent_macro_f1": macro_f1(gold_int, pred_int),
        "intent_accuracy_by_segment": {k: {"acc": round(sum(v) / len(v), 4), "n": len(v)}
                                       for k, v in sorted(seg_acc.items())},
        "language_accuracy": round(sum(p is not None and p.language == r["language"]
                                       for r, p in zip(rows, preds, strict=True)) / len(rows), 4),
        "code_switch_accuracy": round(
            sum(p is not None and p.is_code_switched == r["code_switched"]
                for r, p in zip(rows, preds, strict=True)) / len(rows), 4),
        "slot_crop": slot_prf([r["crop"] for r in rows],
                              [p.entities.crop if p else None for p in preds]),
        "slot_district": slot_prf([r["district"] for r in rows],
                                  [p.entities.district_name if p else None for p in preds]),
        "latency_ms_median": round(sorted(latencies)[len(latencies) // 2], 2),
        "top_confusions": [{"gold": g, "pred": p, "count": c}
                           for (g, p), c in confusions.most_common(10)],
        "errors_detail": [{"id": r["id"], "text": r["text"], "gold": g, "pred": p}
                          for r, g, p in zip(rows, gold_int, pred_int, strict=True) if g != p],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--providers", nargs="+", default=["rule-based-nlu"])
    args = ap.parse_args()
    rows = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line]
    config = {"providers": args.providers, "dataset": str(DATA.relative_to(ML_ROOT)),
              "n": len(rows), "label_status": "draft-unreviewed"}
    results = {}
    with track_experiment("nlu_eval", config, seed=None, split_id="nlu-utterances-v1") as rec:
        for name in args.providers:
            results[name] = asyncio.run(run(name, rows))
            print(name, json.dumps({k: v for k, v in results[name].items()
                                    if k not in {"errors_detail", "top_confusions"}},
                                   ensure_ascii=False))
        rec.metrics = {k: {m: v for m, v in r.items() if m != "errors_detail"}
                       for k, r in results.items()}
        out = REPORTS_DIR / "data" / f"nlu_eval_{rec.run_id}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"run_id": rec.run_id, "config": config, "results": results},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        rec.artifact_path = str(out.relative_to(REPORTS_DIR.parent))
    print("run_id", rec.run_id, "->", rec.artifact_path)


if __name__ == "__main__":
    main()
