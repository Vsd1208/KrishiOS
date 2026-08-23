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

    # ── Sprint 6: Neo4j graph store ────────────────────────────────────────────
    graph_store = None
    try:
        from app.graph.store.neo4j_store import Neo4jGraphStore
        from app.graph.api.dependencies import set_graph_store
        
        neo4j_uri = f"bolt://{settings.NEO4J_HOST}:{settings.NEO4J_PORT}"
        graph_store = Neo4jGraphStore(
            uri=neo4j_uri,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD,
            database=settings.NEO4J_DATABASE,
        )
        reachable = await graph_store.verify_connectivity()
        if reachable:
            await graph_store.ensure_constraints()
            set_graph_store(graph_store)
            logger.info("Neo4j graph store initialised at {}", neo4j_uri)
        else:
            logger.warning("Neo4j not reachable at {} — graph features degraded", neo4j_uri)
    except Exception as exc:
        logger.warning("Neo4j init failed (graph features degraded): {}", exc)

    yield

    # ── Shutdown ───────────────────────────────────────────────────────────────
    if graph_store is not None:
        try:
            await graph_store.close()
        except Exception:
            pass
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

