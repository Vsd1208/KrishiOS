import asyncio

from app.config.settings import get_settings
from app.retrieval.providers.qdrant import QdrantRetrievalVectorStore


async def main() -> None:
    settings = get_settings()

    vector_store = QdrantRetrievalVectorStore(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
    )

    live_state = await vector_store.get_alias_state(
        settings.RETRIEVAL_LIVE_ALIAS
    )

    delta_state = await vector_store.get_alias_state(
        settings.RETRIEVAL_DELTA_ALIAS
    )

    print("\n=== RETRIEVAL INDEX STATE ===")
    print("Live alias:")
    print(live_state)

    print("\nDelta alias:")
    print(delta_state)


if __name__ == "__main__":
    asyncio.run(main())