"""TTS evaluation: CPU latency / real-time factor, plus an ASR round-trip intelligibility proxy.

For each language, N sentences (FLEURS test transcriptions, public text) are synthesised; the
audio is transcribed by an STT provider and CER against the input text is reported. That CER
is a PROXY for intelligibility only (it mixes TTS and ASR errors). Naturalness needs native
listener ratings, which are pending.

Usage (from backend/)::

    uv run --extra local-ml --with jiwer python ../ml/scripts/run_tts_eval.py \
        --tts mms-tts --stt faster-whisper-small --languages te hi --n 20 --seed 13
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import random
import statistics
import time

import _bootstrap  # noqa: F401

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import DATA_DIR, REPORTS_DIR
from krishios_ml.voice.evaluation.wer import error_rates

FLEURS = {"te": "te_in", "hi": "hi_in"}


def sentences(lang: str, n: int, seed: int) -> list[str]:
    path = DATA_DIR / "raw" / "fleurs" / FLEURS[lang] / "test.tsv"
    with path.open(encoding="utf-8") as fh:
        rows = {r[0]: r[2] for r in csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)}
    texts = sorted(rows.values())
    return random.Random(seed).sample(texts, min(n, len(texts)))


async def evaluate(tts_name: str, stt_name: str, lang: str, texts: list[str]) -> dict:
    from app.voice.providers.selection import stt_selector, tts_selector

    tts, stt = tts_selector.get(tts_name), stt_selector.get(stt_name)
    t0 = time.perf_counter()
    await tts.synthesize(texts[0], lang)  # warm-up / model load
    load_s = time.perf_counter() - t0
    lat, rtf, durs, hyps = [], [], [], []
    for text in texts:
        res = await tts.synthesize(text, lang)
        lat.append(res.inference_ms)
        durs.append(res.duration_seconds)
        rtf.append(res.inference_ms / 1000 / max(res.duration_seconds, 1e-6))
        hyps.append((await stt.transcribe(res.audio_path, hint_language=lang)).raw_transcript)
    rates = error_rates(texts, hyps)
    return {
        "language": lang,
        "n": len(texts),
        "latency_ms_median": round(statistics.median(lat), 1),
        "latency_ms_p90": round(sorted(lat)[int(0.9 * (len(lat) - 1))], 1),
        "rtf_median": round(statistics.median(rtf), 3),
        "audio_s_median": round(statistics.median(durs), 2),
        "warmup_and_load_s": round(load_s, 1),
        "asr_roundtrip_cer_proxy": rates.cer,
        "asr_roundtrip_wer_proxy": rates.wer,
        "examples": [{"text": t, "asr": h} for t, h in list(zip(texts, hyps, strict=True))[:2]],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tts", required=True)
    ap.add_argument("--stt", default="faster-whisper-small")
    ap.add_argument("--languages", nargs="+", default=["te", "hi"])
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()
    config = {"tts": args.tts, "stt_for_proxy": args.stt, "n": args.n,
              "languages": args.languages, "texts": "FLEURS test transcriptions", "device": "cpu"}
    results = {}
    with track_experiment("tts_eval", config, seed=args.seed,
                          split_id=f"fleurs-text-sample{args.n}-seed{args.seed}") as rec:
        for lang in args.languages:
            results[lang] = asyncio.run(evaluate(args.tts, args.stt, lang,
                                                 sentences(lang, args.n, args.seed)))
            print(json.dumps({k: v for k, v in results[lang].items() if k != "examples"},
                             ensure_ascii=False))
        rec.metrics = {k: {m: v for m, v in r.items() if m != "examples"}
                       for k, r in results.items()}
        out = REPORTS_DIR / "data" / f"tts_{args.tts}_{rec.run_id}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"run_id": rec.run_id, "config": config, "results": results},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        rec.artifact_path = str(out.relative_to(REPORTS_DIR.parent))
    print("run_id", rec.run_id, "->", rec.artifact_path)


if __name__ == "__main__":
    main()
