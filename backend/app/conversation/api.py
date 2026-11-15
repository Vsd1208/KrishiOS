"""Conversation API (Phase 3): text and voice turns, state, synthesized audio."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthContext, RequirePermission
from app.auth.permissions import Permission
from app.config.settings import get_settings
from app.conversation.manager import FarmerProfile, TurnInput
from app.conversation.service import build_manager, db_sink, get_state_store
from app.database.session import get_db_session
from app.media.service import match_media

router = APIRouter(prefix="/conversation", tags=["Conversation"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
User = Annotated[AuthContext, Depends(RequirePermission(Permission.CONVERSATION_USE))]
LANG = "^(en|hi|te)$"


class ProfileIn(BaseModel):
    district_lgd_code: int | None = None
    crops: list[str] = Field(default_factory=list, max_length=20)


class TurnIn(BaseModel):
    text: str = Field(default="", max_length=2000)
    language: str = Field(pattern=LANG)
    conversation_id: str | None = Field(default=None, max_length=32)
    choice: dict[str, Any] | None = None
    speak: bool = False
    profile: ProfileIn | None = None
    act_as_farmer_id: int | None = None
    bulletin_uuid: str | None = Field(default=None, max_length=36)


async def _authorize_act_as(session: AsyncSession, auth: AuthContext,
                            farmer_id: int | None) -> None:
    if farmer_id is not None:
        from app.extension.service import check_act_as  # noqa: PLC0415

        await check_act_as(session, auth, farmer_id)


def _profile(p: ProfileIn | None) -> FarmerProfile | None:
    return FarmerProfile(district_lgd_code=p.district_lgd_code, crops=p.crops) if p else None


@router.post("/turns")
async def text_turn(body: TurnIn, session: DbSession, auth: User) -> dict:
    """One dialogue turn. ``status`` is answered | clarification | smalltalk | refused."""
    if not body.text.strip() and not body.choice:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "text or choice required")
    await _authorize_act_as(session, auth, body.act_as_farmer_id)
    context_en, profile = None, _profile(body.profile)
    if body.bulletin_uuid:
        from app.govconnect.api import bulletin_context  # noqa: PLC0415

        context_en, bulletin_profile = await bulletin_context(session, auth, body.bulletin_uuid)
        profile = profile or bulletin_profile
    manager = build_manager(sink=db_sink(session, channel="text"))
    result = await manager.handle(TurnInput(
        user_uuid=str(auth.user_uuid), text=body.text, language=body.language,
        conversation_id=body.conversation_id, choice=body.choice, speak=body.speak,
        profile=profile, acting_for_farmer_id=body.act_as_farmer_id, auth=auth,
        context_en=context_en, bulletin_uuid=body.bulletin_uuid,
    ))
    await _attach_media(session, result)
    return result.to_dict()


async def _attach_media(session: AsyncSession, result) -> None:
    """Verified how-to videos for answered questions (F7); never for clarifications."""
    if result.status == "answered":
        result.media = await match_media(session, crop=result.slots.get("crop"),
                                         intent=result.intent, symptoms=result.symptoms,
                                         language=result.language)


@router.post("/voice-turns", dependencies=[Depends(RequirePermission(Permission.VOICE_SUBMIT))])
async def voice_turn(  # noqa: PLR0913, PLR0917 - multipart form fields
    session: DbSession, auth: User,
    file: Annotated[UploadFile, File(description="Recorded question (wav/webm/mp3/m4a/ogg)")],
    language: Annotated[str, Form(pattern=LANG)],
    conversation_id: Annotated[str | None, Form(max_length=32)] = None,
    speak: Annotated[bool, Form()] = True,
    act_as_farmer_id: Annotated[int | None, Form()] = None,
) -> dict:
    """Speech -> text (STT with the farmer's language as hint) -> the same dialogue turn."""
    from app.voice.providers.selection import get_stt_provider  # noqa: PLC0415
    from app.voice.services.storage import AudioStorageService  # noqa: PLC0415
    from app.voice.services.validator import AudioValidator  # noqa: PLC0415

    await _authorize_act_as(session, auth, act_as_farmer_id)
    data = await file.read()
    check = AudioValidator().validate(data, file.content_type)
    if not check.valid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, ", ".join(check.errors))
    storage = AudioStorageService()
    path = await storage.save_audio(data, storage.compute_hash(data), file.filename or "q.wav")
    stt = await get_stt_provider().transcribe(path, hint_language=language)
    if not stt.raw_transcript.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No speech recognised")
    manager = build_manager(sink=db_sink(session, channel="voice"))
    result = await manager.handle(TurnInput(
        user_uuid=str(auth.user_uuid), text=stt.raw_transcript, language=language,
        conversation_id=conversation_id, speak=speak, acting_for_farmer_id=act_as_farmer_id,
        auth=auth,
    ))
    await _attach_media(session, result)
    out = result.to_dict()
    out["transcript"] = stt.raw_transcript
    out["providers"]["stt"] = {"provider": stt.model_name, "version": stt.model_version}
    return out


@router.get("/{conversation_id}")
async def get_state(conversation_id: str, auth: User) -> dict:
    state = await get_state_store().get(conversation_id)
    if state is None or state.user_uuid != str(auth.user_uuid):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return {"conversation_id": state.conversation_id, "language": state.language,
            "crop": state.crop, "district_lgd_code": state.district_lgd_code,
            "district_name": state.district_name, "season": state.season,
            "pending": state.pending.slot if state.pending else None,
            "history": state.history}


@router.get("/audio/{audio_uuid}", response_class=FileResponse)
async def get_audio(audio_uuid: str, auth: User) -> FileResponse:
    """Synthesized reply audio (unguessable UUID file name)."""
    if not audio_uuid.replace("-", "").isalnum():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "bad id")
    path = Path(get_settings().AUDIO_STORAGE_PATH) / "tts" / f"{audio_uuid}.wav"
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audio not found")
    return FileResponse(path, media_type="audio/wav")
