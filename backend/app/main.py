"""FastAPI application factory for the KrishiOS backend."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.api.router import api_router
from app.config.settings import get_settings
from app.core.constants import APP_CONTACT_NAME, APP_DESCRIPTION, APP_LICENSE_NAME
from app.database.session import dispose_database_engine
from app.exceptions.handlers import register_exception_handlers
from app.logging.config import configure_logging
from app.middleware.cors import configure_cors


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage application startup and shutdown lifecycle."""
    settings = get_settings()
    logger.info("{} starting", settings.APP_NAME)
    yield
    await dispose_database_engine()
    logger.info("{} stopped", settings.APP_NAME)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.APP_NAME,
        description=APP_DESCRIPTION,
        version=settings.APP_VERSION,
        contact={"name": APP_CONTACT_NAME},
        license_info={"name": APP_LICENSE_NAME},
        debug=settings.DEBUG,
        lifespan=lifespan,
    )
    configure_cors(app, settings)
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_PREFIX)
    return app


app = create_app()

