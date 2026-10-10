"""Audit event endpoints (read-only, org-scoped)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.models.audit import AuditEvent
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.audit import AuditEventOut
from app.schemas.common import Page
from app.security.auth import OrgContext, get_org_context

router = APIRouter(prefix="/organizations/{org_id}/audit", tags=["audit"])


@router.get("", response_model=Page[AuditEventOut])
def list_audit_events(
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(get_org_context),
    action: str | None = Query(default=None, max_length=128),
    resource_type: str | None = Query(default=None, max_length=64),
    resource_id: str | None = Query(default=None, max_length=128),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    query = db.query(AuditEvent).filter(AuditEvent.organization_id == ctx.org.id)
    if action:
        query = query.filter(AuditEvent.action == action)
    if resource_type:
        query = query.filter(AuditEvent.resource_type == resource_type)
    if resource_id:
        query = query.filter(AuditEvent.resource_id == resource_id)

    total = query.count()
    events = query.order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset).all()

    actor_ids = {e.actor_id for e in events if e.actor_id}
    usernames = (
        {u.id: u.username for u in db.query(User).filter(User.id.in_(actor_ids)).all()}
        if actor_ids
        else {}
    )

    items = [
        AuditEventOut(
            id=e.id,
            organization_id=e.organization_id,
            actor_id=e.actor_id,
            action=e.action,
            resource_type=e.resource_type,
            resource_id=e.resource_id,
            sanitized_detail=e.sanitized_detail,
            request_id=e.request_id,
            created_at=e.created_at,
            actor_username=usernames.get(e.actor_id) if e.actor_id else None,
        )
        for e in events
    ]
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    }
