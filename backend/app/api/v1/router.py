"""Aggregate all v1 routers into a single APIRouter."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    action_items,
    audit,
    auth,
    export,
    health,
    incidents,
    organizations,
    playbooks,
    reports,
    services,
    timeline,
    ws,
)

api_router = APIRouter()

# Health/readiness/metrics are mounted at the app root (no /api/v1 prefix).
health_router = APIRouter()
health_router.include_router(health.router)

api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(services.router)
api_router.include_router(incidents.router)
api_router.include_router(timeline.router)
api_router.include_router(action_items.router)
api_router.include_router(playbooks.router_playbooks)
api_router.include_router(playbooks.router_runs)
api_router.include_router(audit.router)
api_router.include_router(reports.router)
api_router.include_router(export.router)
api_router.include_router(ws.router)
