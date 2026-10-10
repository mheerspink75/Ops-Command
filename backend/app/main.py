"""FastAPI application factory.

Wires together configuration, middleware (request ids, metrics, CORS), error
handling, observability, and the versioned API. Refuses to start in production
with insecure defaults.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.v1.router import api_router, health_router
from app.config import get_settings
from app.core.errors import DomainError
from app.core.ids import normalize_request_id
from app.observability.logging import configure_logging, get_logger
from app.observability.metrics import record_http_request
from app.observability.otel import setup_tracing
from app.realtime.hub import hub

logger = get_logger(__name__)


def _validate_production_settings(settings) -> None:
    if settings.is_production and settings.enforce_secure_secret:
        if settings.secret_key == "insecure-dev-secret-change-me":
            raise RuntimeError(
                "Refusing to start in production with the insecure default SECRET_KEY. "
                "Set a strong SECRET_KEY environment variable."
            )


def create_app() -> FastAPI:
    settings = get_settings()
    _validate_production_settings(settings)
    configure_logging(json_logs=not settings.debug)
    setup_tracing()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        hub.start_redis_bridge()
        logger.info("app.started", extra={"version": __version__})
        yield
        hub.stop_redis_bridge()
        logger.info("app.stopped")

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = normalize_request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        response.headers["X-Request-ID"] = request_id
        # Skip metrics for the metrics endpoint itself to avoid recursion noise.
        if not request.url.path.endswith("/metrics"):
            record_http_request(request.method, response.status_code, duration)
        return response

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        return JSONResponse(status_code=exc.status_code, content=exc.to_envelope())

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                    "details": {"errors": exc.errors()},
                }
            },
        )

    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "service": settings.app_name,
            "version": __version__,
            "docs": "/docs",
            "api": settings.api_v1_prefix,
        }

    return app


app = create_app()
