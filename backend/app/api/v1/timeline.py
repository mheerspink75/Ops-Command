"""Timeline event endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.v1.serializers import serialize_timeline
from app.db.session import get_db
from app.realtime.hub import hub
from app.schemas.common import Page
from app.schemas.timeline import TimelineEventCreate, TimelineEventOut
from app.security.auth import OrgContext, get_org_context, require_role
from app.services import incident_service

router = APIRouter(
    prefix="/organizations/{org_id}/incidents/{incident_id}/timeline",
    tags=["timeline"],
)


@router.post("", response_model=TimelineEventOut, status_code=201)
def add_event(
    incident_id: uuid.UUID,
    payload: TimelineEventCreate,
    request: Request,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(require_role("responder")),
) -> TimelineEventOut:
    event = incident_service.add_timeline_event(
        db,
        incident_id=incident_id,
        org_id=ctx.org.id,
        actor=ctx.user,
        event_type=payload.event_type,
        message=payload.message,
        metadata=payload.metadata,
        request_id=request.headers.get("X-Request-ID"),
    )
    out = serialize_timeline(db, event)
    hub.publish(
        str(incident_id),
        {"type": "timeline_added", "event": out.model_dump(mode="json")},
    )
    return out


@router.get("", response_model=Page[TimelineEventOut])
def list_events(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(get_org_context),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    incident = incident_service._load_incident(db, incident_id, ctx.org.id)
    events = sorted(incident.timeline, key=lambda e: e.created_at)
    total = len(events)
    page = events[offset : offset + limit]
    items = [serialize_timeline(db, e) for e in page]
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    }
