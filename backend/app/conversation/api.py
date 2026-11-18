"""Conversation API (Phase 3): text and voice turns, state, synthesized audio."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from loguru import logger
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
    await _record_diagnosis(session, auth, result)  # after a crop-confirmation chip
    return result.to_dict()


async def _record_diagnosis(session: AsyncSession, auth: AuthContext, result) -> None:
    """F8: an answered photo question with a known district becomes one surveillance report
    (pseudonymous; healthy findings are not stored). A failure here never costs the farmer
    the answer, and the savepoint leaves the rest of the turn's writes intact."""
    from app.surveillance.service import record  # noqa: PLC0415

    v = result.vision or {}
    lgd, crop = result.slots.get("district_lgd_code"), result.slots.get("crop")
    conds = v.get("candidate_conditions") or []
    if result.status != "answered" or not (v and lgd and crop and conds):
        return
    try:
        async with session.begin_nested():
            await record(session, user_uuid=str(auth.user_uuid), lgd_district_code=int(lgd),
                         crop=crop, condition=conds[0]["name"],
                         confidence=float(conds[0]["confidence"]),
                         confirmed=bool(v.get("crop_confirmed_by_farmer")),
                         model_version=str(v.get("model_version") or "unknown"))
        await session.commit()
    except Exception as exc:  # no values logged: this is farmer-linked data
        logger.warning("surveillance report not stored: {}", type(exc).__name__)


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


def _retake(language: str, key: str, conversation_id: str | None, **extra: Any) -> dict:
    from app.conversation.messages import message  # noqa: PLC0415

    return {"conversation_id": conversation_id, "status": "retake", "language": language,
            "reply_text": message(key, language), **extra}


@router.post("/photo-turns", dependencies=[Depends(RequirePermission(Permission.VISION_ANALYZE))])
async def photo_turn(  # noqa: PLR0913, PLR0917 - multipart form fields
    session: DbSession, auth: User,
    file: Annotated[UploadFile, File(description="Crop photo (jpeg/png/webp)")],
    language: Annotated[str, Form(pattern=LANG)],
    text: Annotated[str, Form(max_length=2000)] = "",
    conversation_id: Annotated[str | None, Form(max_length=32)] = None,
    district_lgd_code: Annotated[int | None, Form()] = None,
    crops: Annotated[str, Form(max_length=400)] = "",
) -> dict:
    """Photo -> local crop/disease model -> the same dialogue turn. Low confidence or an
    unsupported crop gives a crop-confirmation clarification; a blurry photo or no plant asks
    for a retake. With a district, the diagnosis is recorded for outbreak surveillance (F8)."""
    from app.config.settings import get_settings as _s  # noqa: PLC0415
    from app.conversation.manager import vision_to_dict  # noqa: PLC0415
    from app.conversation.messages import message  # noqa: PLC0415
    from app.knowledge.storage.file_store import FileStore  # noqa: PLC0415
    from app.vision.providers.selection import get_vision_provider  # noqa: PLC0415
    from app.vision.services.quality import QualityAssessor  # noqa: PLC0415
    from app.vision.services.validator import ImageValidator  # noqa: PLC0415

    data = await file.read()
    check = ImageValidator().validate(data, file.content_type)
    if not check.valid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, ", ".join(check.errors))
    store = FileStore(base_dir=_s().IMAGE_STORAGE_PATH)
    path = await store.save(data, FileStore.compute_hash(data), file.filename or "photo.jpg")
    quality = QualityAssessor().assess(Path(path))
    if not quality.usable:
        return _retake(language, "photo_retake", conversation_id, quality_issues=quality.issues)
    v = vision_to_dict(await get_vision_provider().analyze(Path(path), {}))
    top = (v["crop_candidates"] or [["", 0.0]])[0]
    if top[0] == "other:no_plant" and top[1] >= _s().VISION_CROP_CONFIRM_THRESHOLD:
        return _retake(language, "photo_no_plant", conversation_id, vision=v)
    profile = FarmerProfile(district_lgd_code=district_lgd_code,
                            crops=[c for c in crops.split(",") if c])
    manager = build_manager(sink=db_sink(session, channel="photo"))
    result = await manager.handle(TurnInput(
        user_uuid=str(auth.user_uuid), text=text.strip() or message("photo_default_question",
                                                                    language),
        language=language, conversation_id=conversation_id, profile=profile, auth=auth,
        photo={"path": str(path), "vision": v},
    ))
    await _record_diagnosis(session, auth, result)
    out = result.to_dict()
    out["providers"]["vision"] = {"provider": v["model_name"], "version": v["model_version"]}
    return out
