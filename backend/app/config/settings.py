from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "KrishiOS"
    APP_ENV: Literal["local", "development", "staging", "production", "test"] = "local"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    API_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=list)

    # ── PostgreSQL ────────────────────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "krishios"
    POSTGRES_USER: str = "krishios"
    POSTGRES_PASSWORD: str
    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_MAX_OVERFLOW: int = 20

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    # ── Qdrant (Sprint 2) ─────────────────────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "krishios_documents"

    # ── Embedding model (Sprint 2) ────────────────────────────────────────────
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_MODEL_VERSION: str = "v1"

    # ── Document storage (Sprint 2) ───────────────────────────────────────────
    DOCUMENT_STORAGE_PATH: str = "/data/documents"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: Literal["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_JSON: bool = False

    @computed_field
    @property
    def database_url(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    @computed_field
    @property
    def redis_url(self) -> RedisDsn:
        return RedisDsn.build(
            scheme="redis",
            password=self.REDIS_PASSWORD,
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            path=str(self.REDIS_DB),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

