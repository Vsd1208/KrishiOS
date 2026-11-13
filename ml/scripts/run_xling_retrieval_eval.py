"""Cross-lingual retrieval decision (Phase 3): te/hi queries against an English corpus.

Benchmark: FLEURS test transcriptions (CC BY 4.0). Corpus = the 350 unique English sentences;
query = the Telugu or Hindi sentence with the same FLEURS id; exactly one relevant passage.
This is general-domain parallel text, a proxy for "a farmer asks in te/hi, the knowledge base
is English". An agricultural query set needs native review (pending).

Strategies:
  A  current English embedder (all-MiniLM-L6-v2) on raw te/hi queries      (baseline)
  B  paraphrase-multilingual-MiniLM-L12-v2 on raw queries                   (multilingual)
  C  intfloat/multilingual-e5-small ("query:"/"passage:" prefixes)          (multilingual)
  D  IndicTrans2 indic->en translation, then all-MiniLM-L6-v2               (translate-first)

Usage (from backend/)::

    HF_HUB_OFFLINE=1 uv run --extra local-ml python ../ml/scripts/run_xling_retrieval_eval.py
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import time

import _bootstrap  # noqa: F401
import numpy as np

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, REPORTS_DIR

MODELS = {
    "A": ("sentence-transformers/all-MiniLM-L6-v2", "", ""),
    "B": ("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "", ""),
    "C": ("intfloat/multilingual-e5-small", "query: ", "passage: "),
    "D": ("sentence-transformers/all-MiniLM-L6-v2", "", ""),
}
KS = (1, 5, 10)


def load(lang: str) -> dict[str, str]:
    with (DATA_DIR / "raw" / "fleurs" / lang / "test.tsv").open(encoding="utf-8") as fh:
        return {r[0]: r[2] for r in csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)}


def metrics(scores: np.ndarray, gold: list[int]) -> dict[str, float]:
    ranks = []
    for i, g in enumerate(gold):
        order = np.argsort(-scores[i])
        ranks.append(int(np.where(order == g)[0][0]) + 1)
    ranks_arr = np.array(ranks)
    out = {f"recall@{k}": round(float((ranks_arr <= k).mean()), 4) for k in KS}
    out["mrr"] = round(float((1.0 / ranks_arr).mean()), 4)
    return out


async def translate_queries(queries: list[str], lang: str) -> tuple[list[str], float]:
    from app.translation.providers.indictrans2 import IndicTrans2Provider

    provider = IndicTrans2Provider()
    out: list[str] = []
    t0 = time.perf_counter()
    for i in range(0, len(queries), 16):
        out.extend(await provider.translate(queries[i : i + 16], lang, "en"))
    return out, (time.perf_counter() - t0) * 1000 / len(queries)


def main() -> None:
    from sentence_transformers import SentenceTransformer

    ap = argparse.ArgumentParser()
    ap.add_argument("--strategies", nargs="+", default=list(MODELS))
    args = ap.parse_args()

    en = load("en_us")
    corpus_ids = sorted(en)
    corpus = [en[i] for i in corpus_ids]
    index = {cid: n for n, cid in enumerate(corpus_ids)}
    queries = {lang: load(f"{lang}_in") for lang in ("te", "hi")}
    config = {"benchmark": "FLEURS test parallel (en corpus, te/hi queries)",
              "corpus_size": len(corpus), "n_queries": {k: len(v) for k, v in queries.items()},
              "strategies": {s: MODELS[s][0] for s in args.strategies}, "device": "cpu"}
    results: dict[str, dict] = {}
    with track_experiment("xling_retrieval_eval", config, seed=None,
                          split_id="fleurs-test-parallel-v1") as rec:
        for s in args.strategies:
            model_id, qp, pp = MODELS[s]
            model = SentenceTransformer(model_id, device="cpu")
            c_emb = model.encode([pp + c for c in corpus], normalize_embeddings=True,
                                 batch_size=64)
            results[s] = {"model": model_id}
            for lang, qmap in queries.items():
                qids = sorted(qmap)
                texts = [qmap[q] for q in qids]
                extra_ms = 0.0
                if s == "D":
                    texts, extra_ms = asyncio.run(translate_queries(texts, lang))
                t0 = time.perf_counter()
                q_emb = model.encode([qp + t for t in texts], normalize_embeddings=True,
                                     batch_size=64)
                embed_ms = (time.perf_counter() - t0) * 1000 / len(texts)
                m = metrics(q_emb @ c_emb.T, [index[q] for q in qids])
                m.update({"n": len(qids), "embed_ms_per_query": round(embed_ms, 2),
                          "translate_ms_per_query": round(extra_ms, 1)})
                results[s][lang] = m
                print(s, lang, json.dumps(m), flush=True)
        rec.metrics = results
        out = REPORTS_DIR / "data" / f"xling_retrieval_{rec.run_id}.json"
        out.write_text(json.dumps({"run_id": rec.run_id, "config": config, "results": results},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        rec.artifact_path = str(out.relative_to(REPORTS_DIR.parent))
    print("run_id", rec.run_id, "->", rec.artifact_path)


if __name__ == "__main__":
    main()
