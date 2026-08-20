"""Audio storage service reusing FileStore abstraction."""

from pathlib import Path
from loguru import logger

from app.config.settings import get_settings
from app.knowledge.storage.file_store import FileStore


class AudioStorageService:
    """Wrapper around FileStore for persistent audio storage."""

    def __init__(self) -> None:
        settings = get_settings()
        self._file_store = FileStore(base_dir=settings.AUDIO_STORAGE_PATH)

    @property
    def file_store(self) -> FileStore:
        return self._file_store

    def compute_hash(self, file_bytes: bytes) -> str:
        return FileStore.compute_hash(file_bytes)

    async def save_audio(self, file_bytes: bytes, file_hash: str, filename: str) -> Path:
        return await self._file_store.save(file_bytes, file_hash, filename)

    async def delete_audio(self, storage_path: str | Path) -> bool:
        return await self._file_store.delete(storage_path)

    def exists(self, storage_path: str | Path) -> bool:
        return self._file_store.exists(storage_path)
