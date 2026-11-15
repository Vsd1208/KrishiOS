"""MT evaluation on the agri source set (ml/evaluation_sets/mt/source_en.tsv).

Metrics per provider and target language:
* check_pass_rate: share of sentences whose final translation passes all safety checks
  (numbers, units, protected terms, no leftover placeholders); with span protection.
* number_preservation (protected vs unprotected ablation): among sentences containing numbers,
  share with no missing or extra numbers.
* unit_preservation / protected_term_preservation (with protection).
* placeholder_survival: placeholders restored / placeholders emitted.
* roundtrip_chrfpp: chrF++ of en->xx->en back-translation against the English source. This is
  a PROXY for adequacy only; reference-based chrF++ needs native references
  (references_template.tsv) and is not reported until they exist.

Usage (from backend/)::

    uv run --extra local-ml --with sacrebleu python ../ml/scripts/run_mt_eval.py \
        --providers opus-mt gemini-translate indictrans2 --targets te hi
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import time

import _bootstrap  # noqa: F401
import sacrebleu

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import ML_ROOT, REPORTS_DIR

SPLITS = {
    "test": ML_ROOT / "evaluation_sets" / "mt" / "source_en.tsv",
    "dev": ML_ROOT / "evaluation_sets" / "mt" / "source_en_dev.tsv",
}
SOURCE = SPLITS["test"]
BATCH = 16
# None = each provider's own protect_kinds; set via --kinds for dev-set strategy comparisons.
KINDS_OVERRIDE: frozenset[str] | None = None


def load_source(split: str = "test") -> list[dict]:
    with SPLITS[split].open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


async def _batched(provider, texts: list[str], src: str, tgt: str) -> tuple[list[str], float]:
    out: list[str] = []
    t0 = time.perf_counter()
    for i in range(0, len(texts), BATCH):
        out.extend(await provider.translate(texts[i : i + BATCH], src, tgt))
    return out, (time.perf_counter() - t0) * 1000 / max(len(texts), 1)


async def eval_provider(name: str, tgt: str, rows: list[dict]) -> dict:
    from app.translation.checks import check_translation, extract_numbers
    from app.translation.protect import Protector
    from app.translation.selection import translation_selector

    try:
        provider = translation_selector.get(name)
        if not provider.supports("en", tgt):
            return {"error": "unsupported pair"}
        sources = [r["text"] for r in rows]
        protector = Protector()
        fmt = getattr(provider, "placeholder_format", None)
        kinds = KINDS_OVERRIDE if KINDS_OVERRIDE is not None else getattr(
            provider, "protect_kinds", None)
        masked = [protector.mask(s, "en", tgt, placeholder=fmt, kinds=kinds) for s in sources]
        raw_masked, ms_per = await _batched(provider, [m.text for m in masked], "en", tgt)
        raw_plain, _ = await _batched(provider, sources, "en", tgt)
    except Exception as exc:  # provider unavailable (e.g. gated model) -> recorded
        return {"error": f"{type(exc).__name__}: {str(exc)[:200]}"}

    restored, emitted, survived = [], 0, 0
    for m, out in zip(masked, raw_masked, strict=True):
        text, missing = Protector.restore(out, m.spans)
        restored.append(text)
        emitted += len(m.spans)
        survived += len(m.spans) - len(missing)

    checks = [check_translation(s, t) for s, t in zip(sources, restored, strict=True)]
    ablate = [check_translation(s, t) for s, t in zip(sources, raw_plain, strict=True)]
    with_numbers = [i for i, s in enumerate(sources) if extract_numbers(s)]

    def num_ok(c):
        return not c.missing_numbers and not c.extra_numbers

    passed_idx = [i for i, c in enumerate(checks) if c.passed]
    chrf, roundtrip_error = None, None
    if passed_idx and provider.supports(tgt, "en"):
        try:  # the reverse model may be unavailable (gated / not yet downloaded)
            back, _ = await _batched(provider, [restored[i] for i in passed_idx], tgt, "en")
            chrf = sacrebleu.corpus_chrf(
                back, [[sources[i] for i in passed_idx]], word_order=2).score
        except Exception as exc:
            roundtrip_error = type(exc).__name__

    from app.translation.checks import extract_units

    has_units = [i for i, s in enumerate(sources) if extract_units(s)]
    return {
        "n_sentences": len(sources),
        "check_pass_rate": round(len(passed_idx) / len(sources), 4),
        "number_preservation_protected": round(
            sum(num_ok(checks[i]) for i in with_numbers) / max(len(with_numbers), 1), 4),
        "number_preservation_unprotected": round(
            sum(num_ok(ablate[i]) for i in with_numbers) / max(len(with_numbers), 1), 4),
        "n_with_numbers": len(with_numbers),
        "unit_preservation": round(
            sum(not checks[i].missing_units for i in has_units) / max(len(has_units), 1), 4),
        "n_with_units": len(has_units),
        "protected_term_preservation": round(
            sum(not c.missing_protected_terms for c in checks) / len(checks), 4),
        "placeholder_survival": round(survived / max(emitted, 1), 4),
        "placeholders_emitted": emitted,
        "roundtrip_chrfpp_proxy": round(chrf, 2) if chrf is not None else None,
        "roundtrip_n": len(passed_idx) if chrf is not None else 0,
        "roundtrip_error": roundtrip_error,
        "ms_per_sentence": round(ms_per, 1),
        "failure_reasons_top": _top_reasons(checks),
        "examples": [{"src": sources[i], "out": restored[i], "passed": checks[i].passed}
                     for i in (0, 1, len(sources) - 1)],
    }


def _top_reasons(checks) -> dict[str, int]:
    counts: dict[str, int] = {}
    for c in checks:
        for r in c.reasons:
            key = r.split(" [")[0]
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--providers", nargs="+", default=["opus-mt"])
    ap.add_argument("--targets", nargs="+", default=["te", "hi"])
    ap.add_argument("--split", choices=sorted(SPLITS), default="test")
    ap.add_argument("--kinds", nargs="*", default=None,
                    help="span kinds to protect (quantity protected crop); default: provider's")
    args = ap.parse_args()
    global KINDS_OVERRIDE
    KINDS_OVERRIDE = frozenset(args.kinds) if args.kinds is not None else None
    rows = load_source(args.split)
    from app.providers.device import resolve_device

    config = {"providers": args.providers, "targets": args.targets, "device": resolve_device(),
              "source_set": str(SPLITS[args.split].relative_to(ML_ROOT)), "n": len(rows),
              "protect_kinds_override": sorted(KINDS_OVERRIDE) if KINDS_OVERRIDE else None,
              "checker": "v2 (rs.-boundary fix, bracketless <ID placeholders)",
              "reference_chrf": "pending native refs"}
    results: dict = {}
    split_id = "mt-source-en-v1" if args.split == "test" else "mt-source-en-dev-v1"
    with track_experiment("mt_eval", config, seed=None, split_id=split_id) as rec:
        for name in args.providers:
            for tgt in args.targets:
                res = asyncio.run(eval_provider(name, tgt, rows))
                results[f"{name}:en-{tgt}"] = res
                print(name, tgt, json.dumps({k: v for k, v in res.items()
                                             if k not in {"examples"}}, ensure_ascii=False))
        rec.metrics = {k: {m: v for m, v in r.items() if m != "examples"}
                       for k, r in results.items()}
        out = REPORTS_DIR / "data" / f"mt_eval_{rec.run_id}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"run_id": rec.run_id, "config": config, "results": results},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        rec.artifact_path = str(out.relative_to(REPORTS_DIR.parent))
    print("run_id", rec.run_id, "->", rec.artifact_path)


if __name__ == "__main__":
    main()
