"""Multi-turn dialogue evaluation (Phase 3): task success per language.

Measures **dialogue management**: intent routing, slot filling, clarification and resumption,
carry-over, smalltalk and refusal. It uses the production ConversationManager, NLU, catalog,
LGD and translation policy. The agent runtime is replaced by a fixed grounded answer, so
answer quality and grounded-citation rate are NOT measured here (they need the live knowledge
base).

A dialogue succeeds only if every turn meets every expectation (status, intent, crop,
district, clarified slot). Scripts and labels: DRAFT, pending native review.

Usage (from backend/)::

    uv run python ../ml/scripts/run_dialogue_eval.py
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict

import _bootstrap  # noqa: F401

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import ML_ROOT, REPORTS_DIR

DATA = ML_ROOT / "evaluation_sets" / "dialogue" / "dialogues_v1.jsonl"


class StubRunner:
    async def run(self, ctx):
        from app.conversation.answer import AssembledAnswer

        return AssembledAnswer(text_en="Stub grounded answer.", grounded=True, confidence=0.8,
                               citations=[{"title": "stub"}], agents=["stub"])


def check(result, expect: dict) -> list[str]:
    errors = []
    pairs = {
        "status": result.status,
        "intent": result.intent,
        "crop": result.slots.get("crop"),
        "district": result.slots.get("district_lgd_code"),
        "clarify": (result.clarification or {}).get("slot"),
    }
    for key, want in expect.items():
        if pairs[key] != want:
            errors.append(f"{key}: expected {want!r}, got {pairs[key]!r}")
    return errors


async def run_dialogue(d: dict) -> tuple[bool, list[dict]]:
    from app.conversation.manager import (
        ConversationManager,
        FarmerProfile,
        TurnInput,
    )

    bot = ConversationManager(runner=StubRunner())
    profile = FarmerProfile(**d["profile"]) if d.get("profile") else None
    cid, log, ok = None, [], True
    for t in d["turns"]:
        r = await bot.handle(TurnInput(user_uuid="eval", text=t.get("text", ""),
                                       language=d["language"], conversation_id=cid,
                                       choice=t.get("choice"), profile=profile))
        cid = r.conversation_id
        errs = check(r, t["expect"])
        ok = ok and not errs
        log.append({"text": t.get("text") or t.get("choice"), "errors": errs})
    return ok, log


def main() -> None:
    dialogues = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines()
                 if line.strip()]
    config = {"dataset": str(DATA.relative_to(ML_ROOT)), "n_dialogues": len(dialogues),
              "runtime": "stubbed (dialogue management only)", "label_status": "draft"}
    per_lang: dict[str, list[bool]] = defaultdict(list)
    turns_ok = turns_total = 0
    failures = []
    with track_experiment("dialogue_eval", config, seed=None, split_id="dialogues-v1") as rec:
        for d in dialogues:
            ok, log = asyncio.run(run_dialogue(d))
            per_lang[d["language"]].append(ok)
            turns_total += len(log)
            turns_ok += sum(1 for t in log if not t["errors"])
            if not ok:
                failures.append({"id": d["id"], "turns": log})
        rec.metrics = {
            "task_success": round(sum(sum(v) for v in per_lang.values()) / len(dialogues), 4),
            "task_success_by_language": {k: {"rate": round(sum(v) / len(v), 4), "n": len(v)}
                                         for k, v in sorted(per_lang.items())},
            "turn_accuracy": round(turns_ok / turns_total, 4),
            "n_turns": turns_total,
            "failures": failures,
        }
        print(json.dumps({k: v for k, v in rec.metrics.items() if k != "failures"}))
        for f in failures:
            print("FAIL", f["id"], [t["errors"] for t in f["turns"] if t["errors"]])
        out = REPORTS_DIR / "data" / f"dialogue_eval_{rec.run_id}.json"
        out.write_text(json.dumps({"run_id": rec.run_id, "config": config,
                                   "metrics": rec.metrics}, ensure_ascii=False, indent=1),
                       encoding="utf-8")
        rec.artifact_path = str(out.relative_to(REPORTS_DIR.parent))
    print("run_id", rec.run_id, "->", rec.artifact_path)


if __name__ == "__main__":
    main()
