"""STT evaluation on FLEURS (te_in, hi_in) test splits. Logs to ml/experiments/stt_eval.jsonl.

Usage (from backend/)::

    uv run --extra local-ml --with jiwer python ../ml/scripts/run_stt_eval.py \
        --provider faster-whisper-small --languages te hi --n 50 --seed 13

The sample is drawn with a fixed seed from the FLEURS test split. Language ID is evaluated
without a hint (as in production), and WER/CER is computed with LID as decided by the model.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import random
import statistics
import tarfile
import time
from pathlib import Path

import _bootstrap  # noqa: F401  (sys.path setup)

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, REPORTS_DIR
from krishios_ml.voice.evaluation.wer import error_rates

FLEURS = {"te": "te_in", "hi": "hi_in"}


def load_sample(lang: str, n: int, seed: int) -> list[dict]:
    root = DATA_DIR / "raw" / "fleurs" / FLEURS[lang]
    with (root / "test.tsv").open(encoding="utf-8") as fh:
        rows = [{"id": r[0], "file": r[1], "raw": r[2], "norm": r[3]}
                for r in csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)]
    # FLEURS repeats a sentence across speakers; keep the first recording per sentence id.
    unique = list({r["id"]: r for r in reversed(rows)}.values())
    rng = random.Random(seed)
    sample = sorted(rng.sample(unique, min(n, len(unique))), key=lambda r: r["file"])
    out_dir = DATA_DIR / "interim" / "fleurs" / FLEURS[lang]
    out_dir.mkdir(parents=True, exist_ok=True)
    wanted = {r["file"] for r in sample if not (out_dir / r["file"]).exists()}
    if wanted:
        with tarfile.open(root / "test.tar.gz") as tar:
            for member in tar:
                name = Path(member.name).name
                if name in wanted and member.isfile():
                    src = tar.extractfile(member)
                    if src is not None:
                        (out_dir / name).write_bytes(src.read())
    for r in sample:
        r["path"] = out_dir / r["file"]
    return sample


async def evaluate(provider_name: str, lang: str, sample: list[dict]) -> dict:
    from app.voice.providers.selection import stt_selector

    provider = stt_selector.get(provider_name)
    hyps, latencies, rtfs, lid_ok, switched = [], [], [], 0, 0
    t_load = time.perf_counter()
    await provider.transcribe(sample[0]["path"])  # warm-up (model load); not timed below
    load_s = time.perf_counter() - t_load
    for r in sample:
        res = await provider.transcribe(r["path"])
        hyps.append(res.raw_transcript)
        latencies.append(res.inference_ms)
        if "real_time_factor" in res.metadata:
            rtfs.append(res.metadata["real_time_factor"])
        lid_ok += res.detected_language == lang
        switched += res.is_code_switched
    rates = error_rates([r["raw"] for r in sample], hyps)
    return {
        "language": lang,
        "wer": rates.wer,
        "cer": rates.cer,
        "n_utterances": rates.n_utterances,
        "n_ref_words": rates.n_ref_words,
        "lid_accuracy": round(lid_ok / len(sample), 4),
        "flagged_code_switched": switched,
        "latency_ms_median": round(statistics.median(latencies), 1),
        "latency_ms_p90": round(sorted(latencies)[int(0.9 * (len(latencies) - 1))], 1),
        "rtf_median": round(statistics.median(rtfs), 3) if rtfs else None,
        "warmup_and_load_s": round(load_s, 1),
        "examples": [{"ref": r["raw"], "hyp": h}
                     for r, h in list(zip(sample, hyps, strict=True))[:3]],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True)
    ap.add_argument("--languages", nargs="+", default=["te", "hi"])
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()

    config = {"provider": args.provider, "dataset": "google/fleurs test", "n": args.n,
              "languages": args.languages, "lid_hint": None, "device": "cpu"}
    results = {}
    with track_experiment("stt_eval", config, seed=args.seed,
                          split_id=f"fleurs-test-sample{args.n}-seed{args.seed}") as rec:
        for lang in args.languages:
            sample = load_sample(lang, args.n, args.seed)
            results[lang] = asyncio.run(evaluate(args.provider, lang, sample))
            print(json.dumps({k: v for k, v in results[lang].items() if k != "examples"}))
        rec.metrics = {lang: {k: v for k, v in r.items() if k != "examples"}
                       for lang, r in results.items()}
        out = REPORTS_DIR / "data" / f"stt_{args.provider}_{rec.run_id}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"run_id": rec.run_id, "config": config, "results": results},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        rec.artifact_path = str(out.relative_to(REPORTS_DIR.parent))
    print("run_id", rec.run_id, "->", rec.artifact_path)


if __name__ == "__main__":
    main()
