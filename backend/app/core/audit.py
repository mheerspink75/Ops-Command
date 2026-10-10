"""Audit service: records privileged mutations as immutable, sanitized events."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.sanitize import sanitize_detail
from app.db.models.audit import AuditEvent


def record_audit(
    session: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | uuid.UUID | None = None,
    detail: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> AuditEvent:
    """Persist an audit event. Detail is sanitized before storage.

    The caller is responsible for committing the surrounding transaction so the
    audit row is written atomically with the mutation it describes.
    """
    event = AuditEvent(
        organization_id=organization_id,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        sanitized_detail=sanitize_detail(detail),
        request_id=request_id,
    )
    session.add(event)
    return event
