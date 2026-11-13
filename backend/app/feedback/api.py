"""Feedback API (F13): submit, officer dashboard summary, triage, regression export."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission
from app.auth.permissions import Permission
from app.database.session import get_db_session
from app.models.conversation import ConversationTurnRecord
from app.models.feedback import AnswerFeedback

router = APIRouter(prefix="/feedback", tags=["Feedback"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Submitter = Annotated[AuthContext, Depends(RequirePermission(Permission.FEEDBACK_SUBMIT))]
Reviewer = Annotated[AuthContext, Depends(RequirePermission(Permission.FEEDBACK_REVIEW))]

Reason = Literal["wrong", "unclear", "not_applicable", "unsafe", "translation", "other"]
TriageStatus = Literal["triaged", "converted_to_regression", "dismissed"]


class FeedbackIn(BaseModel):
    target_type: Literal["answer", "bulletin", "diagnosis"]
    target_id: str = Field(min_length=1, max_length=64)
    rating: Literal["up", "down"]
    useful: bool | None = None
    correct: bool | None = None
    reason: Reason | None = None
    comment: str | None = Field(default=None, max_length=2000)
    language: str | None = Field(default=None, pattern="^(en|hi|te)$")


class TriageIn(BaseModel):
    status: TriageStatus


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit(body: FeedbackIn, session: DbSession, auth: Submitter) -> dict:
    """Rate an answer, bulletin or diagnosis. A thumbs-down on an answer puts the turn in the
    officer review queue (``review_reason=farmer_flagged``)."""
    if body.target_type == "answer":
        turn = await session.scalar(select(ConversationTurnRecord).where(
            ConversationTurnRecord.turn_uuid == body.target_id))
        if turn is None or turn.user_uuid != auth.user_uuid:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Answer not found")
        if body.rating == "down":
            turn.requires_review = True
            turn.review_reason = "farmer_flagged"
    fb = AnswerFeedback(target_type=body.target_type, target_id=body.target_id,
                        user_uuid=auth.user_uuid, rating=body.rating, useful=body.useful,
                        correct=body.correct, reason=body.reason, comment=body.comment,
                        language=body.language)
    session.add(fb)
    await session.commit()
    return {"uuid": str(fb.uuid), "status": fb.status}


@router.get("/summary")
async def summary(session: DbSession, auth: Reviewer) -> dict:
    """Dashboard numbers: counts and down-vote rates by target type, language, intent, reason."""
    rows = (await session.execute(
        select(AnswerFeedback, ConversationTurnRecord.intent, ConversationTurnRecord.language)
        .outerjoin(ConversationTurnRecord,
                   (AnswerFeedback.target_type == "answer")
                   & (ConversationTurnRecord.turn_uuid == AnswerFeedback.target_id))
    )).all()
    total = Counter()
    down = Counter()
    for fb, intent, turn_lang in rows:
        keys = [("all", "all"), ("target_type", fb.target_type),
                ("language", fb.language or turn_lang or "unknown"),
                ("intent", intent or "n/a")]
        for k in keys:
            total[k] += 1
            down[k] += fb.rating == "down"
    breakdown: dict[str, list[dict]] = {}
    for (dim, value), n in sorted(total.items()):
        breakdown.setdefault(dim, []).append(
            {"value": value, "count": n, "down": down[(dim, value)],
             "down_rate": round(down[(dim, value)] / n, 3)})
    reasons = Counter(fb.reason for fb, _, _ in rows if fb.rating == "down" and fb.reason)
    pending = sum(1 for fb, _, _ in rows if fb.status == "new" and fb.rating == "down")
    return {"total": len(rows), "breakdown": breakdown, "down_reasons": dict(reasons),
            "pending_triage": pending}


@router.get("")
async def list_feedback(session: DbSession, auth: Reviewer, rating: str | None = None,
                        status_filter: str | None = None, limit: int = 100) -> list[dict]:
    q = select(AnswerFeedback, ConversationTurnRecord).outerjoin(
        ConversationTurnRecord,
        (AnswerFeedback.target_type == "answer")
        & (ConversationTurnRecord.turn_uuid == AnswerFeedback.target_id))
    if rating:
        q = q.where(AnswerFeedback.rating == rating)
    if status_filter:
        q = q.where(AnswerFeedback.status == status_filter)
    rows = (await session.execute(q.order_by(AnswerFeedback.created_at.desc())
                                  .limit(min(limit, 500)))).all()
    return [{
        "uuid": str(fb.uuid), "target_type": fb.target_type, "target_id": fb.target_id,
        "rating": fb.rating, "useful": fb.useful, "correct": fb.correct, "reason": fb.reason,
        "comment": fb.comment, "language": fb.language, "status": fb.status,
        "created_at": fb.created_at.isoformat(),
        "question": t.user_text if t else None, "answer": t.reply_text if t else None,
        "intent": t.intent if t else None,
    } for fb, t in rows]


@router.post("/{feedback_uuid}/triage")
async def triage(feedback_uuid: UUID, body: TriageIn, session: DbSession,
                 auth: Reviewer) -> dict:
    fb = await session.scalar(select(AnswerFeedback).where(AnswerFeedback.uuid == feedback_uuid))
    if fb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback not found")
    fb.status = body.status
    fb.reviewed_by = auth.user_uuid
    fb.reviewed_at = datetime.now(UTC)
    await session.commit()
    return {"uuid": str(fb.uuid), "status": fb.status}


@router.get("/regression-cases")
async def regression_cases(session: DbSession, auth: Reviewer) -> list[dict]:
    """Bad answers converted to regression cases, in the format of
    ``ml/evaluation_sets/regression/*.jsonl`` (append to grow the regression suite)."""
    rows = (await session.execute(
        select(AnswerFeedback, ConversationTurnRecord).join(
            ConversationTurnRecord, ConversationTurnRecord.turn_uuid == AnswerFeedback.target_id)
        .where(AnswerFeedback.target_type == "answer",
               AnswerFeedback.status == "converted_to_regression")
    )).all()
    return [{"id": f"reg-{fb.uuid.hex[:12]}", "question": t.user_text, "language": t.language,
             "intent": t.intent, "slots": t.slots, "bad_answer": t.reply_text,
             "bad_answer_en": t.reply_text_en, "citations": t.citations,
             "reason": fb.reason, "comment": fb.comment,
             "expectation": "answer must differ from bad_answer; officer to add expected facts"}
            for fb, t in rows]
