from dataclasses import dataclass

from loguru import logger
from redis.asyncio import Redis

from app.config.settings import Settings
from app.core.constants import (
    HEALTH_STATUS_DEGRADED,
    HEALTH_STATUS_OK,
    READINESS_STATUS_NOT_READY,
    READINESS_STATUS_READY,
)
from app.database.session import check_database_connection


@dataclass(frozen=True, slots=True)
class HealthService:
    settings: Settings

    def get_root(self) -> dict[str, str]:
        return {
            "name": self.settings.APP_NAME,
            "environment": self.settings.APP_ENV,
            "version": self.settings.APP_VERSION,
        }

    def get_health(self) -> dict[str, str]:
        return {
            "status": HEALTH_STATUS_OK,
            "service": self.settings.APP_NAME,
        }

    def get_version(self) -> dict[str, str]:
        return {
            "version": self.settings.APP_VERSION,
        }

    async def get_readiness(self) -> dict[str, object]:
        checks = {
            "database": await self._database_ready(),
            "redis": await self._redis_ready(),
        }
        is_ready = all(checks.values())

        return {
            "status": READINESS_STATUS_READY if is_ready else READINESS_STATUS_NOT_READY,
            "checks": checks,
        }

    async def _database_ready(self) -> bool:
        try:
            return await check_database_connection()
        except Exception:
            logger.exception("Database readiness check failed")
            return False

    async def _redis_ready(self) -> bool:
        redis = Redis.from_url(str(self.settings.redis_url), decode_responses=True)
        try:
            response = await redis.ping()
            return bool(response)
        except Exception:
            logger.exception("Redis readiness check failed")
            return False
        finally:
            await redis.aclose()


def build_health_status(is_ready: bool) -> str:
    return HEALTH_STATUS_OK if is_ready else HEALTH_STATUS_DEGRADED
