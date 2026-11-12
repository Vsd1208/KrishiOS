import asyncio

from app.config.settings import get_settings
from app.database.session import async_session_factory
from app.retrieval.ingestion.incremental import IncrementalIngestionService
from app.retrieval.providers.embeddings import SentenceTransformerEmbeddingProvider
from app.retrieval.providers.qdrant import QdrantRetrievalVectorStore


async def main():
    settings = get_settings()

    vector_store = QdrantRetrievalVectorStore(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
    )

    embedding_provider = SentenceTransformerEmbeddingProvider(
        model_name=settings.EMBEDDING_MODEL_NAME,
        model_version=settings.EMBEDDING_MODEL_VERSION,
    )

    async with async_session_factory() as session:
        service = IncrementalIngestionService(
            session=session,
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            delta_alias=settings.RETRIEVAL_DELTA_ALIAS,
        )

        for document_id in (6, 7):
            count = await service.ingest_to_delta(
                document_id=document_id,
                alias_name=settings.RETRIEVAL_LIVE_ALIAS,
            )

            print(
                f"document_id={document_id} "
                f"indexed_vectors={count}"
            )

        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
