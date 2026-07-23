from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions.domain import EntityConflictError, EntityNotFoundError, EntityValidationError


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(EntityNotFoundError, entity_not_found_exception_handler)
    app.add_exception_handler(EntityConflictError, entity_conflict_exception_handler)
    app.add_exception_handler(EntityValidationError, entity_validation_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    http_exc = _as_http_exception(exc)
    logger.warning(
        "HTTP exception: method={} path={} status_code={} detail={}",
        request.method,
        request.url.path,
        http_exc.status_code,
        http_exc.detail,
    )
    return JSONResponse(
        status_code=http_exc.status_code,
        content={
            "error": {
                "code": "http_error",
                "message": http_exc.detail,
            },
        },
    )


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    logger.warning(
        "Request validation failed: method={} path={} errors={}",
        request.method,
        request.url.path,
        exc.errors(),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "request_validation_error",
                "message": "Request validation failed",
                "details": exc.errors(),
            },
        },
    )


async def entity_not_found_exception_handler(
    request: Request,
    exc: EntityNotFoundError,
) -> JSONResponse:
    logger.info(
        "Entity not found: method={} path={} detail={}",
        request.method,
        request.url.path,
        str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": {
                "code": "entity_not_found",
                "message": str(exc),
            },
        },
    )


async def entity_conflict_exception_handler(
    request: Request,
    exc: EntityConflictError,
) -> JSONResponse:
    logger.info(
        "Entity conflict: method={} path={} detail={}",
        request.method,
        request.url.path,
        str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": {
                "code": "entity_conflict",
                "message": str(exc),
            },
        },
    )


async def entity_validation_exception_handler(
    request: Request,
    exc: EntityValidationError,
) -> JSONResponse:
    logger.info(
        "Entity validation failed: method={} path={} detail={}",
        request.method,
        request.url.path,
        str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "entity_validation_error",
                "message": str(exc),
            },
        },
    )


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    logger.warning(
        "Application validation failed: method={} path={} errors={}",
        request.method,
        request.url.path,
        exc.errors(),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "application_validation_error",
                "message": "Application validation failed",
            },
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception: method={} path={}",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "Internal server error",
            },
        },
    )


def _as_http_exception(exc: Exception) -> HTTPException | StarletteHTTPException:
    if isinstance(exc, HTTPException | StarletteHTTPException):
        return exc
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
