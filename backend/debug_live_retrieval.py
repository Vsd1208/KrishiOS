import asyncio

from app.config.settings import get_settings
from app.retrieval.interfaces.types import RetrievalFilters
from app.retrieval.providers.embeddings import SentenceTransformerEmbeddingProvider
from app.retrieval.providers.qdrant import QdrantRetrievalVectorStore


async def main() -> None:
    settings = get_settings()

    embedding_provider = SentenceTransformerEmbeddingProvider(
        model_name=settings.EMBEDDING_MODEL_NAME,
        model_version=settings.EMBEDDING_MODEL_VERSION,
    )

    vector_store = QdrantRetrievalVectorStore(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
    )

    query = "what pests affect paddy"

    print("QUERY:", query)

    query_vector = await embedding_provider.embed_query(query)

    print("VECTOR SIZE:", len(query_vector))
    print("LIVE ALIAS:", settings.RETRIEVAL_LIVE_ALIAS)

    results = await vector_store.search_alias(
        alias_name=settings.RETRIEVAL_LIVE_ALIAS,
        query_vector=query_vector,
        top_k=5,
        filters=RetrievalFilters(
            crop="paddy",
            season="kharif",
        ),
        score_threshold=0.0,
    )

    print("HITS:", len(results))

    for index, hit in enumerate(results, start=1):
        print("=" * 80)
        print("HIT:", index)
        print("CHUNK:", hit.chunk_id)
        print("SIMILARITY:", hit.similarity)
        print("COLLECTION:", hit.collection)
        print("METADATA:", hit.metadata)
        print("TEXT:", hit.chunk_text[:800])


if __name__ == "__main__":
    asyncio.run(main())