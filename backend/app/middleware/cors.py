"""CORS middleware registration for browser-accessible API clients."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import Settings


def configure_cors(app: FastAPI, settings: Settings) -> None:
    """Register CORS middleware using configured trusted origins."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

