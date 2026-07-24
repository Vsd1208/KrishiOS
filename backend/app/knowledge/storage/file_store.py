"""File persistence layer with SHA-256 content-addressed deduplication.

Responsibilities
----------------
* Compute SHA-256 hash of uploaded bytes (used for dedup check before write).
* Persist binary content to the configured storage volume.
* Return the absolute storage path for recording in PostgreSQL.

Design decisions
----------------
* Files are stored under a two-level directory structure derived from the
  first 4 hex characters of the hash (e.g. /data/documents/ab/cd/<hash>.<ext>).
  This prevents inode exhaustion in a single flat directory.
* aiofiles is used for non-blocking writes so the event loop is not stalled.
* This module has NO SQLAlchemy dependency — it only deals with the filesystem.
"""

import hashlib
from pathlib import Path

import aiofiles
from loguru import logger


class FileStore:
    """Async file persistence service with SHA-256 deduplication.

    Parameters
    ----------
    base_dir:
        Root directory where all document files are stored.
        Must be writable by the application process.
    """

    def __init__(self, base_dir: str | Path) -> None:
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    # ── Public API ─────────────────────────────────────────────────────────

    @staticmethod
    def compute_hash(file_bytes: bytes) -> str:
        """Return the SHA-256 hex digest of the given bytes.

        This is the sole deduplication key. Callers should query the
        database for existing documents with this hash BEFORE calling
        ``save`` to avoid writing identical files twice.
        """
        return hashlib.sha256(file_bytes).hexdigest()

    async def save(
        self,
        file_bytes: bytes,
        file_hash: str,
        original_filename: str,
    ) -> Path:
        """Persist file bytes to disk and return the storage path.

        If a file with the same hash already exists on disk (e.g. a previous
        orphaned write), the existing file is reused without overwriting.

        Parameters
        ----------
        file_bytes:
            Raw binary content to persist.
        file_hash:
            Pre-computed SHA-256 hex digest (from ``compute_hash``).
        original_filename:
            Used only to preserve the file extension.

        Returns
        -------
        Path
            Absolute path to the stored file.
        """
        suffix = Path(original_filename).suffix.lower()
        dest = self._destination(file_hash, suffix)

        if dest.exists():
            logger.debug("FileStore: reusing existing file at {}", dest)
            return dest

        dest.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest, "wb") as fh:
            await fh.write(file_bytes)

        logger.info(
            "FileStore: saved {} bytes → {} (hash={})",
            len(file_bytes),
            dest,
            file_hash[:12],
        )
        return dest

    async def delete(self, storage_path: str | Path) -> bool:
        """Remove a file from disk.

        Returns True if the file was deleted, False if it did not exist.
        Errors (e.g. permission) are re-raised to the caller.
        """
        path = Path(storage_path)
        if not path.exists():
            logger.warning("FileStore.delete: file not found at {}", path)
            return False
        path.unlink()
        logger.info("FileStore: deleted {}", path)
        return True

    def exists(self, storage_path: str | Path) -> bool:
        """Return True if the file currently exists on disk."""
        return Path(storage_path).exists()

    # ── Internal helpers ────────────────────────────────────────────────────

    def _destination(self, file_hash: str, suffix: str) -> Path:
        """Compute the two-level sharded storage path.

        Example: hash=abcdef…  →  <base>/ab/cd/abcdef….pdf
        """
        shard1 = file_hash[:2]
        shard2 = file_hash[2:4]
        return self._base / shard1 / shard2 / f"{file_hash}{suffix}"
