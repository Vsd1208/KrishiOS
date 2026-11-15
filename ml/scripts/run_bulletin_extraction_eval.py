"""Bulletin extraction accuracy on real NDMA SACHET CAP alerts (Phase 4/5).

Labels are the official structured CAP fields; the extractor sees only the free text
(headline, description, instruction). Built by ``fetch_sachet_sample.py``. Tune on ``dev``
only; ``test`` is scored once per configuration (ADR-013).

Metrics:
- districts: micro precision / recall / F1 over LGD codes, and exact-set match
- severity: accuracy vs CAP severity (Minor/Moderate/Severe/Extreme -> LOW..CRITICAL)
- hazard: accuracy on alerts whose CAP event maps to a KrishiOS hazard class
- valid_to: coverage and share within 60 minutes of CAP ``expires``

Usage (from backend/)::

    uv run python ../ml/scripts/run_bulletin_extraction_eval.py --split dev
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime

import _bootstrap  # noqa: F401

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import ML_ROOT, REPORTS_DIR

TOLERANCE_MIN = 60


def score(rows: list[dict], headline_gold: dict[str, set[int]] | None = None) -> dict:
    from app.govconnect.extraction import get_extractor

    ex = get_extractor()
    tp = fp = fn = exact = 0
    htp = hfp = hfn = 0
    sev_ok = haz_ok = haz_n = vt_cov = vt_ok = 0
    errors: Counter[str] = Counter()
    examples = []
    for r in rows:
        e = ex.extract(r["text"])
        gold, pred = set(r["labels"]["district_codes"]), set(e.value("district_codes", []))
        tp += len(gold & pred)
        fp += len(pred - gold)
        fn += len(gold - pred)
        exact += gold == pred
        hgold = (headline_gold or {}).get(r["text"], gold)
        htp += len(hgold & pred)
        hfp += len(pred - hgold)
        hfn += len(hgold - pred)
        sev_ok += e.value("severity") == r["labels"]["severity"]
        if r["labels"]["hazard"]:
            haz_n += 1
            haz_ok += e.value("hazard_type") == r["labels"]["hazard"]
        vt = e.value("valid_to")
        if vt is not None:
            vt_cov += 1
            gold_vt = datetime.fromisoformat(r["labels"]["valid_to"])
            vt_ok += abs((vt - gold_vt).total_seconds()) <= TOLERANCE_MIN * 60
        if gold != pred:
            errors["district_miss" if gold - pred else "district_extra"] += 1
            if len(examples) < 8:
                examples.append({"id": r["identifier"], "text": r["text"][:200],
                                 "area": r["area_desc"], "gold": sorted(gold),
                                 "pred": sorted(pred)})
    n = len(rows)
    p = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    return {
        "n": n,
        "district_precision": round(p, 4), "district_recall": round(rc, 4),
        "district_f1": round(2 * p * rc / (p + rc), 4) if p + rc else 0.0,
        "district_exact_match": round(exact / n, 4),
        # IMD splits one multi-state headline into per-state alerts; this variant scores
        # against the union of districts over alerts that share the same text.
        "district_precision_headline": round(htp / (htp + hfp), 4) if htp + hfp else 0.0,
        "district_recall_headline": round(htp / (htp + hfn), 4) if htp + hfn else 0.0,
        "severity_accuracy": round(sev_ok / n, 4),
        "hazard_accuracy": round(haz_ok / haz_n, 4) if haz_n else None, "hazard_n": haz_n,
        "valid_to_coverage": round(vt_cov / n, 4),
        "valid_to_within_60min": round(vt_ok / n, 4),
        "error_counts": dict(errors), "district_error_examples": examples,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], required=True)
    ap.add_argument("--data", default="evaluation_sets/govconnect/sachet_20261113.jsonl")
    args = ap.parse_args()
    from app.govconnect.extraction import EXTRACTOR_NAME

    path = ML_ROOT / args.data
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    headline_gold: dict[str, set[int]] = {}
    for r in rows:  # union over the whole snapshot: gold only, no predictions involved
        headline_gold.setdefault(r["text"], set()).update(r["labels"]["district_codes"])
    rows = [r for r in rows if r["split"] == args.split]
    config = {"dataset": args.data, "split": args.split, "extractor": EXTRACTOR_NAME,
              "input": "headline+description+instruction (no structured CAP fields)",
              "labels": "CAP structured fields (official)"}
    with track_experiment("bulletin_extraction_eval", config, seed=13,
                          split_id=f"sachet-20261113-{args.split}") as rec:
        overall = score(rows, headline_gold)
        by_lang = {lang: score([r for r in rows if r["language"] == lang], headline_gold)
                   for lang in sorted({r["language"] for r in rows})}
        rec.metrics = {"overall": overall,
                       "by_language": {k: {m: v for m, v in d.items()
                                           if m != "district_error_examples"}
                                       for k, d in by_lang.items()}}
        out = REPORTS_DIR / "data" / f"bulletin_extraction_{rec.run_id}.json"
        out.write_text(json.dumps({"run_id": rec.run_id, "config": config,
                                   "metrics": rec.metrics}, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        rec.artifact_path = str(out.relative_to(REPORTS_DIR.parent))
    print(json.dumps({k: v for k, v in overall.items() if k != "district_error_examples"}))
    for ex in overall["district_error_examples"]:
        print("ERR", json.dumps(ex, ensure_ascii=False))
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
