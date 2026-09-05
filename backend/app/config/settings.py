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

    RETRIEVAL_INDEX_PREFIX: str = "krishios-index"
    RETRIEVAL_LIVE_ALIAS: str = "krishios-live"
    RETRIEVAL_DELTA_ALIAS: str = "krishios-delta"
    RERANKER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RETRIEVAL_CACHE_TTL_SECONDS: int = 300

    RANKING_WEIGHT_SEMANTIC: float = 0.45
    RANKING_WEIGHT_AUTHORITY: float = 0.15
    RANKING_WEIGHT_FRESHNESS: float = 0.15
    RANKING_WEIGHT_CROP: float = 0.08
    RANKING_WEIGHT_STATE: float = 0.05
    RANKING_WEIGHT_DISTRICT: float = 0.05
    RANKING_WEIGHT_SEASON: float = 0.04
    RANKING_WEIGHT_LANGUAGE: float = 0.03

    # ── Embedding model (Sprint 2) ────────────────────────────────────────────
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_MODEL_VERSION: str = "v1"

    # ── Document storage (Sprint 2) ───────────────────────────────────────────
    DOCUMENT_STORAGE_PATH: str = "/data/documents"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── LLM / Generative AI ─────────────────────────────────────────────────
    LLM_PROVIDER: Literal["gemini", "local"] = "local"
    LLM_MODEL: str = "gemini-3.6-flash"
    GEMINI_API_KEY: str | None = None
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1200
    LLM_TIMEOUT_SECONDS: float = 60.0


    # ── Authentication ────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "insecure-local-dev-key-do-not-use-in-production"
    JWT_ALGORITHM: str = "HS256"

    # ── Neo4j & GraphRAG (Sprint 6) ───────────────────────────────────────────
    NEO4J_HOST: str = "localhost"
    NEO4J_PORT: int = 7687
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "krishios-neo4j-secret"
    NEO4J_DATABASE: str = "neo4j"
    
    # Graph extraction confidence thresholds
    GRAPH_AUTO_ACCEPT_THRESHOLD: float = 0.80
    GRAPH_REVIEW_REQUIRED_THRESHOLD: float = 0.50

    # GraphRAG fusion weights
    GRAPHRAG_WEIGHT_VECTOR: float = 0.50
    GRAPHRAG_WEIGHT_GRAPH: float = 0.50

    # ── Vision / Crop Intelligence (Sprint 7) ─────────────────────────────────
    IMAGE_STORAGE_PATH: str = "/data/images"
    MAX_IMAGE_UPLOAD_SIZE_MB: int = 15
    IMAGE_MAX_DIMENSION: int = 4096
    IMAGE_MIN_DIMENSION: int = 224
    IMAGE_ALLOWED_MIMES: list[str] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp"]
    )

    # Vision model
    VISION_MODEL_NAME: str = "mock-v1"
    VISION_MODEL_VERSION: str = "0.1.0"

    # Quality and confidence thresholds
    VISION_QUALITY_MIN_SCORE: float = 0.3
    VISION_CONFIDENCE_THRESHOLD: float = 0.5

    # Analysis caching
    VISION_CACHE_TTL_SECONDS: int = 3600

    # ── Voice / Multilingual Intelligence (Sprint 8) ──────────────────────────
    AUDIO_STORAGE_PATH: str = "/data/audio"
    MAX_AUDIO_UPLOAD_SIZE_MB: int = 25
    MAX_AUDIO_DURATION_SECONDS: int = 180
    AUDIO_ALLOWED_MIMES: list[str] = Field(
        default_factory=lambda: [
            "audio/wav",
            "audio/x-wav",
            "audio/mpeg",
            "audio/mp3",
            "audio/m4a",
            "audio/mp4",
            "audio/webm",
            "audio/ogg",
        ]
    )

    STT_PROVIDER_NAME: str = "mock-stt-v1"
    STT_MODEL_VERSION: str = "0.1.0"
    TTS_PROVIDER_NAME: str = "mock-tts-v1"
    TTS_MODEL_VERSION: str = "0.1.0"

    VOICE_CACHE_TTL_SECONDS: int = 3600

    # ── Live Agricultural Intelligence (Sprint 9) ────────────────────────────
    WEATHER_PROVIDER_NAME: str = "mock-weather-v1"
    WEATHER_API_BASE_URL: str = "https://api.open-meteo.com/v1"
    WEATHER_CACHE_TTL_SECONDS: int = 1800  # 30 mins
    WEATHER_FORECAST_CACHE_TTL_SECONDS: int = 7200  # 2 hours

    MARKET_PROVIDER_NAME: str = "mock-market-v1"
    MARKET_API_BASE_URL: str = "https://api.data.gov.in/resource"
    MARKET_CACHE_TTL_SECONDS: int = 21600  # 6 hours

    ADVISORY_PROVIDER_NAME: str = "mock-advisory-v1"
    ADVISORY_CACHE_TTL_SECONDS: int = 43200  # 12 hours

    SCHEME_PROVIDER_NAME: str = "mock-scheme-v1"
    SCHEME_CACHE_TTL_SECONDS: int = 86400  # 24 hours

    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIME_SECONDS: float = 30.0
    CIRCUIT_BREAKER_TIMEOUT_SECONDS: float = 5.0
    LIVE_DATA_RATE_LIMIT_PER_MINUTE: int = 60

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

