"""REST endpoints for enterprise retrieval and index management."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Response, status

from app.config.settings import Settings
from app.config.settings import get_settings
from app.database.session import async_session_factory
from app.retrieval.api.dependencies import get_index_service, get_search_service
from app.retrieval.api.schemas import (
    IndexBuildRequest,
    IndexPromoteRequest,
    IndexResponse,
    IndexRollbackRequest,
    IndexStatusResponse,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
)
from app.retrieval.services.index_service import RetrievalIndexService
from app.retrieval.services.search_service import RetrievalSearchService

router = APIRouter(tags=["Enterprise Retrieval"])


@router.post("/indexes/build", response_model=IndexResponse, status_code=status.HTTP_202_ACCEPTED)
async def build_index(
    request: IndexBuildRequest,
    service: Annotated[RetrievalIndexService, Depends(get_index_service)],
) -> IndexResponse:
    """Build and validate a new immutable retrieval index version."""
    index = await service.build(request)
    return IndexResponse.model_validate(index)


@router.post("/indexes/promote", response_model=IndexResponse)
async def promote_index(
    request: IndexPromoteRequest,
    service: Annotated[RetrievalIndexService, Depends(get_index_service)],
) -> IndexResponse:
    """Promote a validated index using blue-green alias switching."""
    index = await service.promote(request.index_id)
    return IndexResponse.model_validate(index)


@router.post("/indexes/rollback", response_model=IndexResponse)
async def rollback_index(
    request: IndexRollbackRequest,
    service: Annotated[RetrievalIndexService, Depends(get_index_service)],
) -> IndexResponse:
    """Rollback the live alias to the previous production index."""
    index = await service.rollback(request.alias_name)
    return IndexResponse.model_validate(index)


@router.get("/indexes", response_model=list[IndexResponse])
async def list_indexes(
    service: Annotated[RetrievalIndexService, Depends(get_index_service)],
) -> list[IndexResponse]:
    """List retrieval index versions."""
    indexes = await service.list_indexes()
    return [IndexResponse.model_validate(index) for index in indexes]


@router.get("/indexes/status", response_model=IndexStatusResponse)
async def index_status(
    service: Annotated[RetrievalIndexService, Depends(get_index_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IndexStatusResponse:
    """Return current live alias and version history."""
    return await service.status(settings.RETRIEVAL_LIVE_ALIAS)


@router.post("/retrieval/search", response_model=RetrievalSearchResponse)
async def search_retrieval(
    request: RetrievalSearchRequest,
    service: Annotated[RetrievalSearchService, Depends(get_search_service)],
) -> RetrievalSearchResponse:
    """Run enterprise semantic retrieval without LLM generation."""
    return await service.search(request)


@router.post("/indexes/build/background", status_code=status.HTTP_202_ACCEPTED)
async def build_index_background(
    request: IndexBuildRequest,
    background_tasks: BackgroundTasks,
) -> Response:
    """Schedule index build work after returning an API response."""
    background_tasks.add_task(_run_background_build, request)
    return Response(status_code=status.HTTP_202_ACCEPTED)


async def _run_background_build(request: IndexBuildRequest) -> None:
    """Run a retrieval index build with resources independent of the request lifecycle."""
    from app.retrieval.api.dependencies import get_embedding_provider, get_vector_store
    from app.retrieval.indexing.manager import IndexManager

    settings = get_settings()
    async with async_session_factory() as session:
        manager = IndexManager(
            session=session,
            vector_store=get_vector_store(),
            embedding_provider=get_embedding_provider(),
            index_prefix=settings.RETRIEVAL_INDEX_PREFIX,
        )
        await manager.build_index(
            alias_name=request.alias_name,
            index_kind=request.index_kind,
            build_mode=request.build_mode,
            source_document_type=request.source_document_type,
        )
