"""Phase 10c: does search find the page that answers each question? (no LLM involved)

For every answerable item of ``reference/assistant_qset_v1.json`` and each language, the backend's
``/retrieval/search`` is called and the rank of the first passage from the cited guide within one
page of the cited page is recorded (answers often run across a page break). Reports hit@1, hit@5
and MRR per language. The question set is a draft under review, so this is a diagnostic of the
retrieval stack, not a final score.

Usage (from ml/, backend running)::

    python scripts/eval_assistant_retrieval.py [--split dev|test|all] [--translated] [--top-k 5]

``--translated`` searches Hindi/Telugu questions through their English translation
(``reference/assistant_qset_v1_query_en.json``, IndicTrans2 indic-en), as the assistant would.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from statistics import mean

import _bootstrap  # noqa: F401

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import ML_ROOT, REPORTS_DIR

QSET = ML_ROOT / "reference" / "assistant_qset_v1.json"
QUERY_EN = ML_ROOT / "reference" / "assistant_qset_v1_query_en.json"
TITLES = {  # question-set source key -> document title in the knowledge base
    "pau_kharif": "Package of Practices for Kharif Crops",
    "pau_rabi": "Package of Practices for Rabi Crops",
    "tnau_agri": "Crop Production Guide: Agriculture (2020)",
}
PAGE_SLACK = 1


def search(api: str, query: str, top_k: int) -> dict:
    body = json.dumps({"query": query, "top_k": top_k}).encode()
    req = urllib.request.Request(f"{api}/retrieval/search", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:8000/api/v1")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    ap.add_argument("--translated", action="store_true")
    args = ap.parse_args()
    qset = json.loads(QSET.read_text(encoding="utf-8"))
    items = [it for it in qset["items"] if it["answerable"]
             and (args.split == "all" or it.get("split") == args.split)]
    translations = (json.loads(QUERY_EN.read_text(encoding="utf-8")) if args.translated
                    else None)
    config = {"qset": qset["version"], "split": args.split, "items": len(items),
              "top_k": args.top_k, "page_slack": PAGE_SLACK, "endpoint": "/retrieval/search",
              "query_translation": translations["provider"] if translations else None}
    with track_experiment("assistant_retrieval", config, seed=None,
                          split_id=qset["version"]) as rec:
        rows = []
        for it in items:
            for lang, q in it["q"].items():
                if translations and lang != "en":
                    q = translations["translations"][it["id"]][lang]
                res = search(args.api, q, args.top_k)
                rank = None
                for i, r in enumerate(res.get("results") or [], start=1):
                    c = r.get("citation") or {}
                    page = c.get("page_number")
                    if (c.get("title") == TITLES[it["source"]] and page is not None
                            and abs(int(page) - it["page"]) <= PAGE_SLACK):
                        rank = i
                        break
                rows.append({"id": it["id"], "lang": lang, "rank": rank,
                             "latency_ms": round(res.get("latency_ms") or 0.0, 1),
                             "top": [((r.get("citation") or {}).get("title"),
                                      (r.get("citation") or {}).get("page_number"))
                                     for r in (res.get("results") or [])[:3]]})
                print(it["id"], lang, rank, flush=True)
        by_lang = {}
        for lang in ("en", "hi", "te"):
            if not any(r["lang"] == lang for r in rows):
                continue
            ranks = [r["rank"] for r in rows if r["lang"] == lang]
            by_lang[lang] = {"n": len(ranks),
                             "hit@1": round(mean(r == 1 for r in ranks), 3),
                             f"hit@{args.top_k}": round(mean(r is not None for r in ranks), 3),
                             "mrr": round(mean(1 / r if r else 0 for r in ranks), 3),
                             "median_latency_ms": sorted(x["latency_ms"] for x in rows
                                                         if x["lang"] == lang)[len(ranks) // 2]}
        rec.metrics = by_lang
        path = REPORTS_DIR / "data" / f"assistant_retrieval_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config, "by_lang": by_lang,
                                    "rows": rows}, indent=1, ensure_ascii=False),
                        encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
    print(json.dumps(by_lang, indent=1))
    print("run_id", rec.run_id)


if __name__ == "__main__":
    main()
