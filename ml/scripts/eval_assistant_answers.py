"""Phase 10c: score the assistant's answers on the question set (runs with the backend's Python).

For each item and language, ``AssistantService.ask`` runs end to end (translation, search, the
on-device LLM, translation back). Automatic, provisional scores per language:

- answerable items: answered share, key-fact recall in the English answer (facts as written in
  the guide), and citation accuracy (a cited passage from the right guide within one page);
- uncovered items: correct abstention share;
- speed: median total seconds.

Hindi/Telugu correctness still needs a human: every answer is written to the report for review.

Usage (from backend/, env as for the backend; Ollama serving the model)::

    python ../ml/scripts/eval_assistant_answers.py --split dev [--ollama http://127.0.0.1:11435]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from statistics import median

ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML / "src"))
sys.path.insert(0, str(ML.parent / "backend"))

from app.agents.providers.llm import OllamaLLMProvider  # noqa: E402
from app.agents.runtime.factory import _build_retrieval_pipeline  # noqa: E402
from app.assistant.service import AssistantService, Passage  # noqa: E402
from app.retrieval.interfaces.types import RetrievalFilters  # noqa: E402
from app.translation.service import TranslationService  # noqa: E402

from krishios_ml.common.experiment_log import track_experiment  # noqa: E402
from krishios_ml.common.paths import REPORTS_DIR  # noqa: E402

QSET = ML / "reference" / "assistant_qset_v1.json"
TITLES = {"pau_kharif": "Package of Practices for Kharif Crops",
          "pau_rabi": "Package of Practices for Rabi Crops",
          "tnau_agri": "Crop Production Guide: Agriculture (2020)"}
SCRIPT = {"hi": r"[ऀ-ॿ]", "te": r"[ఀ-౿]"}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().replace("\u2013", "-"))  # en dash as hyphen


def make_search():
    pipeline = _build_retrieval_pipeline()

    async def search(query_en: str, top_k: int) -> list[Passage]:
        res = await pipeline.search(query_en, RetrievalFilters(), top_k, 0.0, include_delta=True)
        return [Passage(r.hit.chunk_text, r.citation.title, r.citation.page_number,
                        r.citation.source_url, r.hit.similarity) for r in res.results]
    return search


async def run(args: argparse.Namespace) -> None:
    qset = json.loads(QSET.read_text(encoding="utf-8"))
    items = [it for it in qset["items"] if args.split == "all" or it["split"] == args.split]
    llm = OllamaLLMProvider(args.ollama, args.model, timeout_seconds=600)
    service = AssistantService(llm, make_search(), TranslationService())
    config = {"qset": qset["version"], "split": args.split, "topics": len(items),
              "model": args.model, "runtime": "ollama", "top_k": 5,
              "translation": "TranslationService (TRANSLATION_PROVIDER)"}
    with track_experiment("assistant_answers", config, seed=None,
                          split_id=qset["version"]) as rec:
        rows = []
        for it in items:
            for lang, q in it["q"].items():
                out = await service.ask(q, lang)
                row = {"id": it["id"], "lang": lang, "answerable": it["answerable"],
                       "answered": out.answered, "question": q, "query_en": out.query_en,
                       "answer": out.answer, "answer_en": out.answer_en,
                       "citations": out.citations, "translation_failed": out.translation_failed,
                       "seconds": round(out.timings_ms.get("total", 0) / 1000, 1)}
                if it["answerable"] and out.answered:
                    facts = it["key_facts"]
                    row["fact_recall"] = (sum(norm(f) in norm(out.answer_en) for f in facts)
                                          / len(facts)) if facts else None
                    row["citation_ok"] = any(
                        c["title"] == TITLES[it["source"]] and c["page"] is not None
                        and abs(int(c["page"]) - it["page"]) <= 1 for c in out.citations)
                if lang in SCRIPT and out.answered and not out.translation_failed:
                    row["in_script"] = bool(re.search(SCRIPT[lang], out.answer))
                rows.append(row)
                print(it["id"], lang, "answered" if out.answered else "declined",
                      row.get("fact_recall"), row.get("citation_ok"), row["seconds"], flush=True)
        by_lang = {}
        for lang in ("en", "hi", "te"):
            ans = [r for r in rows if r["lang"] == lang and r["answerable"]]
            unans = [r for r in rows if r["lang"] == lang and not r["answerable"]]
            got = [r for r in ans if r["answered"]]
            by_lang[lang] = {
                "answerable": len(ans), "answered": round(len(got) / len(ans), 3) if ans else None,
                "fact_recall_when_answered": round(sum(r["fact_recall"] for r in got)
                                                   / len(got), 3) if got else None,
                "citation_ok_when_answered": round(sum(r["citation_ok"] for r in got)
                                                   / len(got), 3) if got else None,
                "uncovered": len(unans),
                "declined_uncovered": round(sum(not r["answered"] for r in unans)
                                            / len(unans), 3) if unans else None,
                "translation_failed": sum(r["translation_failed"] for r in rows
                                          if r["lang"] == lang),
                "median_seconds": median(r["seconds"] for r in rows if r["lang"] == lang)}
        rec.metrics = by_lang
        path = REPORTS_DIR / "data" / f"assistant_answers_{rec.run_id}.json"
        path.write_text(json.dumps({"run_id": rec.run_id, "config": config, "by_lang": by_lang,
                                    "rows": rows}, indent=1, ensure_ascii=False),
                        encoding="utf-8")
        rec.artifact_path = str(path.relative_to(REPORTS_DIR.parent))
    print(json.dumps(by_lang, indent=1))
    print("run_id", rec.run_id)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    ap.add_argument("--ollama", default="http://127.0.0.1:11435")
    ap.add_argument("--model", default="qwen2.5:3b")
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
