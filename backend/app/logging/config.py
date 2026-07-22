import logging
import sys
from collections.abc import Mapping
from types import FrameType
from typing import Any

from loguru import logger

from app.config.settings import Settings


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame: FrameType | None = logging.currentframe()
        depth = 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging(settings: Settings) -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        serialize=settings.LOG_JSON,
        backtrace=settings.DEBUG,
        diagnose=settings.DEBUG,
        enqueue=True,
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    for logger_name in _third_party_logger_names():
        logging.getLogger(logger_name).handlers = [InterceptHandler()]
        logging.getLogger(logger_name).propagate = False

    logger.bind(
        app_name=settings.APP_NAME,
        app_env=settings.APP_ENV,
        app_version=settings.APP_VERSION,
    ).info("Logging configured")


def bind_log_context(context: Mapping[str, Any]) -> None:
    logger.configure(extra=dict(context))


def _third_party_logger_names() -> tuple[str, ...]:
    return (
        "alembic",
        "asyncio",
        "fastapi",
        "sqlalchemy",
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
    )
