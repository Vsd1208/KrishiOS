"""NLU API (Sprint 11)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies.auth import RequirePermission
from app.auth.permissions import Permission
from app.nlu import service

router = APIRouter(prefix="/nlu", tags=["NLU"])


class ParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language_hint: str | None = Field(default=None, pattern="^(en|hi|te)$")


@router.post("/parse", dependencies=[Depends(RequirePermission(Permission.NLU_USE))])
async def parse(req: ParseRequest) -> dict:
    """Intent + entities (crop via catalog, district via LGD), language and code-switching."""
    result = await service.parse(req.text, req.language_hint)
    return result.to_dict()
