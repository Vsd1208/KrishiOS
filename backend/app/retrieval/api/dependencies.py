"""FastAPI dependencies for retrieval services and providers."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.database.session import get_db_session
from app.retrieval.citations.builder import CitationBuilder
from app.retrieval.indexing.manager import IndexManager
from app.retrieval.providers.embeddings import SentenceTransformerEmbeddingProvider
from app.retrieval.providers.qdrant import QdrantRetrievalVectorStore
from app.retrieval.ranking.engine import RankingEngine, RankingWeights
from app.retrieval.reranking.cross_encoder import CrossEncoderReranker
from app.retrieval.retrieval.context import ContextBuilder
from app.retrieval.retrieval.metadata import QueryMetadataExtractor
from app.retrieval.retrieval.pipeline import EnterpriseRetrievalPipeline
from app.retrieval.services.index_service import RetrievalIndexService
from app.retrieval.services.search_service import RetrievalSearchService


@lru_cache(maxsize=1)
def get_vector_store() -> QdrantRetrievalVectorStore:
    """Return the process-wide vector store provider."""
    settings = get_settings()
    return QdrantRetrievalVectorStore(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


@lru_cache(maxsize=1)
def get_embedding_provider() -> SentenceTransformerEmbeddingProvider:
    """Return the process-wide embedding provider."""
    settings = get_settings()
    return SentenceTransformerEmbeddingProvider(
        model_name=settings.EMBEDDING_MODEL_NAME,
        model_version=settings.EMBEDDING_MODEL_VERSION,
    )


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoderReranker:
    """Return the process-wide cross-encoder reranker."""
    settings = get_settings()
    return CrossEncoderReranker(settings.RERANKER_MODEL_NAME)


def get_index_manager(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IndexManager:
    """Build a request-scoped IndexManager with shared providers."""
    return IndexManager(
        session=session,
        vector_store=get_vector_store(),
        embedding_provider=get_embedding_provider(),
        index_prefix=settings.RETRIEVAL_INDEX_PREFIX,
    )


def get_index_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    manager: Annotated[IndexManager, Depends(get_index_manager)],
) -> RetrievalIndexService:
    """Build the retrieval index application service."""
    return RetrievalIndexService(session=session, index_manager=manager)


def get_search_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RetrievalSearchService:
    """Build the retrieval search application service."""
    pipeline = EnterpriseRetrievalPipeline(
        embedding_provider=get_embedding_provider(),
        vector_store=get_vector_store(),
        reranker=get_reranker(),
        ranking_engine=RankingEngine(
            RankingWeights(
                semantic=settings.RANKING_WEIGHT_SEMANTIC,
                authority=settings.RANKING_WEIGHT_AUTHORITY,
                freshness=settings.RANKING_WEIGHT_FRESHNESS,
                crop=settings.RANKING_WEIGHT_CROP,
                state=settings.RANKING_WEIGHT_STATE,
                district=settings.RANKING_WEIGHT_DISTRICT,
                season=settings.RANKING_WEIGHT_SEASON,
                language=settings.RANKING_WEIGHT_LANGUAGE,
            )
        ),
        context_builder=ContextBuilder(),
        citation_builder=CitationBuilder(),
        metadata_extractor=QueryMetadataExtractor(),
        live_alias=settings.RETRIEVAL_LIVE_ALIAS,
        delta_alias=settings.RETRIEVAL_DELTA_ALIAS,
    )
    return RetrievalSearchService(pipeline)
