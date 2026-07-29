"""Blue-green retrieval index deployment coordinator."""

from app.retrieval.interfaces.providers import VectorStoreProvider
from app.retrieval.interfaces.types import AliasState


class BlueGreenDeploymentService:
    """Perform atomic alias switching and rollback for retrieval indexes."""

    def __init__(self, vector_store: VectorStoreProvider) -> None:
        self._vector_store = vector_store

    async def promote(self, alias_name: str, collection_name: str) -> AliasState:
        """Switch the live alias to a validated collection."""
        return await self._vector_store.switch_alias(alias_name, collection_name)

    async def rollback(self, alias_name: str, previous_collection: str) -> AliasState:
        """Restore the live alias to a previous production collection."""
        return await self._vector_store.switch_alias(alias_name, previous_collection)

    async def current(self, alias_name: str) -> AliasState:
        """Return the current live alias mapping."""
        return await self._vector_store.get_alias_state(alias_name)
