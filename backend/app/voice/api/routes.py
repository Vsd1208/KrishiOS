"""REST API routes for Multilingual Voice Intelligence Platform."""

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RequirePermission, get_current_auth_context, AuthContext
from app.auth.permissions import Permission
from app.database.session import get_db_session

from app.voice.models.audio import AudioRecord
from app.voice.models.transcript import SpeechTranscript
from app.voice.schemas.voice import AudioRecordResponse, TranscriptResponse, VoiceQueryResponse
from app.voice.services.voice_service import VoiceService

router = APIRouter(prefix="/voice", tags=["Voice"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Auth = Annotated[AuthContext, Depends(get_current_auth_context)]


@router.post(
    "/query",
    response_model=VoiceQueryResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RequirePermission(Permission.VOICE_SUBMIT))],
    summary="Submit multilingual voice query for spoken + text advisory",
)
async def submit_voice_query(
    session: DbSession,
    auth: Auth,
    file: Annotated[UploadFile, File(description="Voice query audio file (WAV/MP3/M4A/WEBM)")],
    hint_language: Annotated[str | None, Form(description="Optional hint language ('en', 'hi', 'te')")] = None,
    analysis_id: Annotated[int | None, Form(description="Optional vision analysis ID for voice + image query")] = None,
) -> VoiceQueryResponse:
    """Accepts an audio file upload, performs language detection, speech recognition, normalization, agent execution, localization, and text-to-speech synthesis."""
    file_bytes = await file.read()
    filename = file.filename or "voice_query.wav"

    service = VoiceService(session=session)
    try:
        return await service.process_voice_query(
            file_bytes=file_bytes,
            original_filename=filename,
            content_type=file.content_type,
            auth=auth,
            hint_language=hint_language,
            analysis_id=analysis_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Voice API: query processing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Voice query processing failed: {exc}",
        ) from exc


@router.get(
    "/audio/{audio_uuid}",
    response_model=AudioRecordResponse,
    dependencies=[Depends(RequirePermission(Permission.VOICE_READ_OWN))],
    summary="Get audio recording metadata by UUID",
)
async def get_audio_record(
    audio_uuid: UUID,
    session: DbSession,
    auth: Auth,
) -> AudioRecordResponse:
    stmt = select(AudioRecord).where(AudioRecord.uuid == audio_uuid)
    record = (await session.execute(stmt)).scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Audio record not found")

    if str(record.owner_uuid) != str(auth.user_uuid) and not auth.has_permission(Permission.SYSTEM_ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized to access this audio recording")

    return AudioRecordResponse.model_validate(record)


@router.get(
    "/transcripts/{transcript_uuid}",
    response_model=TranscriptResponse,
    dependencies=[Depends(RequirePermission(Permission.VOICE_READ_OWN))],
    summary="Get speech transcript details by UUID",
)
async def get_transcript(
    transcript_uuid: UUID,
    session: DbSession,
    auth: Auth,
) -> TranscriptResponse:
    stmt = (
        select(SpeechTranscript, AudioRecord)
        .join(AudioRecord, SpeechTranscript.audio_id == AudioRecord.id)
        .where(SpeechTranscript.uuid == transcript_uuid)
    )
    result = (await session.execute(stmt)).first()

    if not result:
        raise HTTPException(status_code=404, detail="Transcript not found")

    transcript, audio = result

    if str(audio.owner_uuid) != str(auth.user_uuid) and not auth.has_permission(Permission.SYSTEM_ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized to access this transcript")

    resp = TranscriptResponse.model_validate(transcript)
    resp.audio_uuid = audio.uuid
    return resp


@router.delete(
    "/audio/{audio_uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequirePermission(Permission.VOICE_DELETE))],
    summary="Delete own audio recording and transcripts",
)
async def delete_audio_record(
    audio_uuid: UUID,
    session: DbSession,
    auth: Auth,
) -> Response:
    stmt = select(AudioRecord).where(AudioRecord.uuid == audio_uuid)
    record = (await session.execute(stmt)).scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Audio record not found")

    if str(record.owner_uuid) != str(auth.user_uuid) and not auth.has_permission(Permission.SYSTEM_ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized to delete this audio recording")

    # Hard-delete from storage and DB
    service = VoiceService(session=session)
    await service._storage.delete_audio(record.storage_key)

    await session.delete(record)
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
