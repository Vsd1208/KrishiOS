import asyncio

from app.config.settings import get_settings
from app.retrieval.providers.qdrant import QdrantRetrievalVectorStore


async def main() -> None:
    settings = get_settings()

    vector_store = QdrantRetrievalVectorStore(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
    )

    points, _ = await vector_store._client.scroll(
        collection_name="krishios-delta-collection",
        limit=100,
        with_payload=True,
        with_vectors=False,
    )

    print("\n=== DELTA INDEX ===")
    print(f"Total points returned: {len(points)}")

    for point in points:
        payload = point.payload or {}

        print("\n--- POINT ---")
        print(f"point_id    : {point.id}")
        print(f"document_id : {payload.get('document_id')}")
        print(f"title       : {payload.get('title')}")
        print(f"crop        : {payload.get('crop')}")
        print(f"state       : {payload.get('state')}")
        print(f"district    : {payload.get('district')}")
        print(f"season      : {payload.get('season')}")
        print(f"page_number : {payload.get('page_number')}")
        print(f"chunk_id    : {payload.get('chunk_id')}")


if __name__ == "__main__":
    asyncio.run(main())