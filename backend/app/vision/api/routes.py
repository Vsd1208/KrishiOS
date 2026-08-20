"""REST API routes for Vision Intelligence."""

import json
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import RequirePermission, get_current_auth_context, AuthContext
from app.auth.permissions import Permission
from app.config.settings import get_settings
from app.database.session import get_db_session, async_session_factory
from app.knowledge.storage.file_store import FileStore
from app.graph.extraction.entity_resolver import EntityResolver

from app.vision.models.image import CropImage
from app.vision.models.analysis import ImageAnalysis, ImageAnalysisStatus
from app.vision.schemas.vision import (
    ImageUploadRequest,
    ImageUploadResponse,
    AnalysisResponse,
    AnalysisListResponse,
)
from app.vision.services.validator import ImageValidator
from app.vision.services.quality import QualityAssessor
from app.vision.services.preprocessor import ImagePreprocessor
from app.vision.providers.mock_provider import MockVisionProvider
from app.vision.pipeline import VisionAnalysisPipeline


router = APIRouter(prefix="/vision", tags=["Vision"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
Auth = Annotated[AuthContext, Depends(get_current_auth_context)]


def get_file_store() -> FileStore:
    settings = get_settings()
    return FileStore(base_dir=settings.IMAGE_STORAGE_PATH)


FileStoreDep = Annotated[FileStore, Depends(get_file_store)]
ImageValidatorDep = Annotated[ImageValidator, Depends(ImageValidator)]


@router.post(
    "/images",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(RequirePermission(Permission.VISION_ANALYZE))],
    summary="Upload image for vision analysis",
)
async def upload_image(
    background_tasks: BackgroundTasks,
    session: DbSession,
    auth: Auth,
    file_store: FileStoreDep,
    validator: ImageValidatorDep,
    file: Annotated[UploadFile, File(description="Crop image to analyze")],
    metadata: Annotated[str, Form(description="JSON-encoded ImageUploadRequest")] = "{}",
) -> ImageUploadResponse:
    """Uploads an image and triggers background analysis."""
    try:
        meta_dict = json.loads(metadata)
        req = ImageUploadRequest(**meta_dict)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid metadata JSON: {exc}",
        )

    file_bytes = await file.read()
    
    # Validation
    val_result = validator.validate(file_bytes, file.content_type)
    if not val_result.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Image validation failed", "errors": val_result.errors}
        )

    file_hash = FileStore.compute_hash(file_bytes)
    
    # Check for duplicate
    stmt = select(CropImage).where(CropImage.file_hash == file_hash)
    existing_img = (await session.execute(stmt)).scalar_one_or_none()
    
    if existing_img:
        if str(existing_img.owner_uuid) != str(auth.user_uuid) and not auth.has_permission(Permission.VISION_READ_FIELD):
            # Same image, different user, not an officer - don't leak existence
            # We should probably store a new record or allow sharing, but for MVP:
            pass 
        else:
            # We already have this image. Let's see if there's an analysis
            stmt = select(ImageAnalysis).where(ImageAnalysis.image_id == existing_img.id).order_by(ImageAnalysis.created_at.desc())
            existing_analysis = (await session.execute(stmt)).scalars().first()
            if existing_analysis:
                return ImageUploadResponse(
                    image_id=existing_img.id,
                    uuid=existing_img.uuid,
                    status=existing_analysis.status
                )

    # Persist file
    filename = file.filename or "upload.jpg"
    storage_path = await file_store.save(file_bytes, file_hash, filename)

    # DB Models
    crop_image = CropImage(
        owner_uuid=auth.user_uuid,
        field_id=None, # req.field_uuid resolution skipped for brevity in MVP
        file_hash=file_hash,
        storage_key=str(storage_path),
        original_filename=filename,
        mime_type=val_result.mime_type,
        width=val_result.width,
        height=val_result.height,
        file_size=len(file_bytes),
        crop_hint=req.crop_hint
    )
    session.add(crop_image)
    await session.commit()
    await session.refresh(crop_image)
    
    settings = get_settings()
    analysis = ImageAnalysis(
        image_id=crop_image.id,
        model_name=settings.VISION_MODEL_NAME,
        model_version=settings.VISION_MODEL_VERSION,
        status=ImageAnalysisStatus.UPLOADED
    )
    session.add(analysis)
    await session.commit()
    await session.refresh(analysis)

    # Schedule background task
    background_tasks.add_task(_run_vision_analysis_background, analysis_id=analysis.id)

    return ImageUploadResponse(
        image_id=crop_image.id,
        uuid=crop_image.uuid,
        status=analysis.status
    )


async def _run_vision_analysis_background(analysis_id: int) -> None:
    settings = get_settings()
    provider = MockVisionProvider(model_name=settings.VISION_MODEL_NAME, model_version=settings.VISION_MODEL_VERSION)
    quality_assessor = QualityAssessor()
    preprocessor = ImagePreprocessor()
    entity_resolver = EntityResolver()

    async with async_session_factory() as session:
        pipeline = VisionAnalysisPipeline(
            session=session,
            provider=provider,
            quality_assessor=quality_assessor,
            preprocessor=preprocessor,
            entity_resolver=entity_resolver,
        )
        await pipeline.run(analysis_id)


@router.get(
    "/analyses/{analysis_uuid}",
    response_model=AnalysisResponse,
    dependencies=[Depends(RequirePermission(Permission.VISION_READ_OWN))],
)
async def get_analysis(
    analysis_uuid: UUID,
    session: DbSession,
    auth: Auth,
) -> AnalysisResponse:
    stmt = (
        select(ImageAnalysis, CropImage)
        .join(CropImage, ImageAnalysis.image_id == CropImage.id)
        .where(ImageAnalysis.uuid == analysis_uuid)
    )
    result = (await session.execute(stmt)).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
        
    analysis, image = result

    # Authorization check
    if str(image.owner_uuid) != str(auth.user_uuid) and not auth.has_permission(Permission.VISION_READ_FIELD):
        raise HTTPException(status_code=403, detail="Not authorized to view this analysis")

    # Map to schema
    # Pydantic's from_attributes handles most of this, but we need to inject image_uuid
    resp = AnalysisResponse.model_validate(analysis)
    resp.image_uuid = image.uuid
    return resp


@router.get(
    "/analyses",
    response_model=AnalysisListResponse,
    dependencies=[Depends(RequirePermission(Permission.VISION_READ_OWN))],
)
async def list_analyses(
    session: DbSession,
    auth: Auth,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AnalysisListResponse:
    """List analyses. Farmers see their own; officers could see jurisdiction (if we pass a filter)."""
    
    stmt = (
        select(ImageAnalysis, CropImage)
        .join(CropImage, ImageAnalysis.image_id == CropImage.id)
    )
    
    # Force isolation unless explicitly bypassing (e.g. system admin)
    # For MVP, officers see all if they have READ_FIELD (in a real system, filter by jurisdiction)
    if not auth.has_permission(Permission.VISION_READ_FIELD):
        stmt = stmt.where(CropImage.owner_uuid == auth.user_uuid)
        
    stmt = stmt.order_by(ImageAnalysis.created_at.desc())
    
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    items = (await session.execute(stmt.offset(offset).limit(limit))).all()
    
    responses = []
    for a, i in items:
        resp = AnalysisResponse.model_validate(a)
        resp.image_uuid = i.uuid
        responses.append(resp)
        
    return AnalysisListResponse(total=total, offset=offset, limit=limit, items=responses)
