"""Incident lifecycle endpoints: create, list, get, update, status, roles."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.v1.serializers import serialize_incident
from app.db.session import get_db
from app.realtime.hub import hub
from app.schemas.common import Page
from app.schemas.incident import (
    IncidentCreate,
    IncidentOut,
    IncidentRoleAssign,
    IncidentRoleAssignmentOut,
    IncidentStatusUpdate,
    IncidentUpdate,
)
from app.security.auth import OrgContext, get_org_context, require_role
from app.services import incident_service

router = APIRouter(prefix="/organizations/{org_id}/incidents", tags=["incidents"])


def _publish(incident_id: uuid.UUID, event_type: str, data: dict) -> None:
    hub.publish(str(incident_id), {"type": event_type, **data})


@router.post("", response_model=IncidentOut, status_code=201)
def create_incident(
    payload: IncidentCreate,
    request: Request,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(require_role("responder")),
) -> IncidentOut:
    incident = incident_service.create_incident(
        db,
        org_id=ctx.org.id,
        actor=ctx.user,
        title=payload.title,
        summary=payload.summary,
        severity=payload.severity,
        service_ids=payload.service_ids,
        commander_id=payload.commander_id,
        request_id=request.headers.get("X-Request-ID"),
    )
    _publish(
        incident.id,
        "incident_created",
        {"incident": serialize_incident(db, incident).model_dump(mode="json")},
    )
    return serialize_incident(db, incident)


@router.get("", response_model=Page[IncidentOut])
def list_incidents(
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(get_org_context),
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    incidents, total = incident_service.search_incidents(
        db,
        org_id=ctx.org.id,
        status=status,
        severity=severity,
        q=q,
        limit=limit,
        offset=offset,
    )
    items = [serialize_incident(db, i) for i in incidents]
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    }


@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(get_org_context),
) -> IncidentOut:
    incident = incident_service._load_incident(db, incident_id, ctx.org.id)
    return serialize_incident(db, incident)


@router.patch("/{incident_id}", response_model=IncidentOut)
def update_incident(
    incident_id: uuid.UUID,
    payload: IncidentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(require_role("responder")),
) -> IncidentOut:
    incident = incident_service.update_incident(
        db,
        incident_id=incident_id,
        org_id=ctx.org.id,
        actor=ctx.user,
        title=payload.title,
        summary=payload.summary,
        severity=payload.severity,
        service_ids=payload.service_ids,
        commander_id=payload.commander_id,
        expected_version=payload.expected_version,
        request_id=request.headers.get("X-Request-ID"),
    )
    _publish(
        incident_id,
        "incident_updated",
        {"incident": serialize_incident(db, incident).model_dump(mode="json")},
    )
    return serialize_incident(db, incident)


@router.post("/{incident_id}/status", response_model=IncidentOut)
def transition_status(
    incident_id: uuid.UUID,
    payload: IncidentStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(require_role("responder")),
) -> IncidentOut:
    incident = incident_service.transition_status(
        db,
        incident_id=incident_id,
        org_id=ctx.org.id,
        actor=ctx.user,
        new_status=payload.status,
        expected_version=payload.expected_version,
        request_id=request.headers.get("X-Request-ID"),
    )
    _publish(
        incident_id,
        "status_changed",
        {
            "status": incident.status,
            "incident": serialize_incident(db, incident).model_dump(mode="json"),
        },
    )
    return serialize_incident(db, incident)


@router.post("/{incident_id}/roles", response_model=IncidentRoleAssignmentOut, status_code=201)
def assign_role(
    incident_id: uuid.UUID,
    payload: IncidentRoleAssign,
    request: Request,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(require_role("responder")),
) -> IncidentRoleAssignmentOut:
    from app.api.v1.serializers import _usernames

    assignment = incident_service.assign_role(
        db,
        incident_id=incident_id,
        org_id=ctx.org.id,
        actor=ctx.user,
        user_id=payload.user_id,
        role=payload.role,
        request_id=request.headers.get("X-Request-ID"),
    )
    uname = _usernames(db, {assignment.user_id})
    out = IncidentRoleAssignmentOut(
        user_id=assignment.user_id,
        role=assignment.role,
        assigned_at=assignment.assigned_at,
        username=uname.get(assignment.user_id),
    )
    _publish(
        incident_id, "role_assigned", {"role": assignment.role, "user_id": str(assignment.user_id)}
    )
    return out


@router.get("/{incident_id}/roles", response_model=list[IncidentRoleAssignmentOut])
def list_roles(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(get_org_context),
) -> list[IncidentRoleAssignmentOut]:
    from app.api.v1.serializers import _usernames

    incident = incident_service._load_incident(db, incident_id, ctx.org.id)
    uname = _usernames(db, {a.user_id for a in incident.role_assignments})
    return [
        IncidentRoleAssignmentOut(
            user_id=a.user_id, role=a.role, assigned_at=a.assigned_at, username=uname.get(a.user_id)
        )
        for a in incident.role_assignments
    ]
