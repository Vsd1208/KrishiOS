"""Scheme eligibility Q&A (F4): deterministic evaluation of officer-verified criteria.

Each criterion is ``{"id", "question": {en,hi,te}, "type": "bool"|"number"|"choice",
"rule": {"op": eq|ne|lte|gte|lt|gt|in|not_in, "value": ...}, "kind": "require"|"exclude",
"source": "..."}``. ``require``: the answer must satisfy the rule. ``exclude``: an answer that
satisfies the rule makes the farmer ineligible. The result is guidance only; the scheme
authority decides, and personal status is never looked up without an official API and consent.
"""

from __future__ import annotations

from typing import Any

OPS = {
    "eq": lambda a, v: a == v,
    "ne": lambda a, v: a != v,
    "lte": lambda a, v: float(a) <= float(v),
    "gte": lambda a, v: float(a) >= float(v),
    "lt": lambda a, v: float(a) < float(v),
    "gt": lambda a, v: float(a) > float(v),
    "in": lambda a, v: a in v,
    "not_in": lambda a, v: a not in v,
}


class CriteriaError(ValueError):
    pass


def validate_criteria(criteria: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for c in criteria:
        cid = c.get("id")
        if not cid or cid in seen:
            raise CriteriaError(f"criterion id missing or duplicated: {cid!r}")
        seen.add(cid)
        if c.get("type") not in {"bool", "number", "choice"}:
            raise CriteriaError(f"{cid}: type must be bool, number or choice")
        if c.get("kind") not in {"require", "exclude"}:
            raise CriteriaError(f"{cid}: kind must be require or exclude")
        rule = c.get("rule") or {}
        if rule.get("op") not in OPS or "value" not in rule:
            raise CriteriaError(f"{cid}: rule needs op in {sorted(OPS)} and a value")
        question = c.get("question") or {}
        if not question.get("en"):
            raise CriteriaError(f"{cid}: an English question is required")
        if not c.get("source"):
            raise CriteriaError(f"{cid}: every criterion must cite its source")


def _coerce(kind: str, answer: Any) -> Any:
    if kind == "bool":
        if isinstance(answer, bool):
            return answer
        if str(answer).lower() in {"true", "yes", "1"}:
            return True
        if str(answer).lower() in {"false", "no", "0"}:
            return False
        raise CriteriaError("expected yes/no")
    if kind == "number":
        return float(answer)
    return answer


def evaluate(
    criteria: list[dict[str, Any]], answers: dict[str, Any], language: str = "en"
) -> dict[str, Any]:
    results, missing, failed = [], [], []
    for c in criteria:
        question = c["question"].get(language) or c["question"]["en"]
        if c["id"] not in answers or answers[c["id"]] in (None, ""):
            missing.append(c["id"])
            results.append({"id": c["id"], "question": question, "answered": False})
            continue
        try:
            value = _coerce(c["type"], answers[c["id"]])
            matches = OPS[c["rule"]["op"]](value, c["rule"]["value"])
        except (CriteriaError, TypeError, ValueError):
            missing.append(c["id"])
            results.append(
                {"id": c["id"], "question": question, "answered": False, "error": "invalid answer"}
            )
            continue
        ok = matches if c["kind"] == "require" else not matches
        if not ok:
            failed.append(c["id"])
        results.append(
            {
                "id": c["id"],
                "question": question,
                "answered": True,
                "met": ok,
                "source": c["source"],
            }
        )
    status = "not_eligible" if failed else "incomplete" if missing else "likely_eligible"
    return {"status": status, "failed": failed, "missing": missing, "criteria": results}
