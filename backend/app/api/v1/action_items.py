"""Action item endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.v1.serializers import serialize_action_item
from app.db.session import get_db
from app.realtime.hub import hub
from app.schemas.action_item import ActionItemCreate, ActionItemOut, ActionItemUpdate
from app.security.auth import OrgContext, get_org_context, require_role
from app.services import incident_service

router = APIRouter(
    prefix="/organizations/{org_id}/incidents/{incident_id}/action-items",
    tags=["action-items"],
)


@router.post("", response_model=ActionItemOut, status_code=201)
def create_item(
    incident_id: uuid.UUID,
    payload: ActionItemCreate,
    request: Request,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(require_role("responder")),
) -> ActionItemOut:
    item = incident_service.create_action_item(
        db,
        incident_id=incident_id,
        org_id=ctx.org.id,
        actor=ctx.user,
        title=payload.title,
        description=payload.description,
        assignee_id=payload.assignee_id,
        status=payload.status,
        due_at=payload.due_at,
        request_id=request.headers.get("X-Request-ID"),
    )
    out = serialize_action_item(db, item)
    hub.publish(
        str(incident_id), {"type": "action_item_added", "item": out.model_dump(mode="json")}
    )
    return out


@router.get("", response_model=list[ActionItemOut])
def list_items(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(get_org_context),
) -> list[ActionItemOut]:
    incident = incident_service._load_incident(db, incident_id, ctx.org.id)
    items = sorted(incident.action_items, key=lambda a: a.created_at)
    return [serialize_action_item(db, i) for i in items]


@router.patch("/{item_id}", response_model=ActionItemOut)
def update_item(
    incident_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ActionItemUpdate,
    request: Request,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(require_role("responder")),
) -> ActionItemOut:
    item = incident_service.update_action_item(
        db,
        incident_id=incident_id,
        org_id=ctx.org.id,
        actor=ctx.user,
        item_id=item_id,
        title=payload.title,
        description=payload.description,
        assignee_id=payload.assignee_id,
        status=payload.status,
        due_at=payload.due_at,
        request_id=request.headers.get("X-Request-ID"),
    )
    out = serialize_action_item(db, item)
    hub.publish(
        str(incident_id), {"type": "action_item_updated", "item": out.model_dump(mode="json")}
    )
    return out
