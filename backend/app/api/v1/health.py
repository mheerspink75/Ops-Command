"""Health, readiness, and metrics endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Response
from sqlalchemy import text

from app.config import get_settings
from app.core.redis_client import get_redis
from app.db.session import get_engine
from app.observability.metrics import render_metrics

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness probe: the process is up."""
    return {"status": "ok", "service": get_settings().app_name}


@router.get("/ready")
def ready() -> Response:
    """Readiness probe: verifies database and Redis connectivity."""
    checks: dict[str, str] = {}
    healthy = True

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc.__class__.__name__}"
        healthy = False

    try:
        get_redis().ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc.__class__.__name__}"
        healthy = False

    status_code = 200 if healthy else 503
    return Response(
        content=json.dumps({"status": "ready" if healthy else "degraded", "checks": checks}),
        status_code=status_code,
        media_type="application/json",
    )


@router.get("/metrics")
def metrics() -> Response:
    """Prometheus-compatible metrics endpoint."""
    return Response(content=render_metrics(), media_type="text/plain; version=0.0.4")
