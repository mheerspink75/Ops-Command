"""API serializers that enrich ORM objects with related display fields."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.db.models.incident import Incident
from app.db.models.user import User
from app.schemas.action_item import ActionItemOut
from app.schemas.incident import IncidentOut, IncidentRoleAssignmentOut
from app.schemas.service import ServiceOut
from app.schemas.timeline import TimelineEventOut


def _usernames(db: Session, user_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not user_ids:
        return {}
    return {u.id: u.username for u in db.query(User).filter(User.id.in_(user_ids)).all()}


def serialize_incident(db: Session, incident: Incident) -> IncidentOut:
    services = [ServiceOut.model_validate(isv.service) for isv in incident.services]
    role_user_ids = {a.user_id for a in incident.role_assignments}
    uname = _usernames(db, role_user_ids)
    roles = [
        IncidentRoleAssignmentOut(
            user_id=a.user_id,
            role=a.role,
            assigned_at=a.assigned_at,
            username=uname.get(a.user_id),
        )
        for a in incident.role_assignments
    ]
    return IncidentOut(
        id=incident.id,
        organization_id=incident.organization_id,
        title=incident.title,
        summary=incident.summary,
        severity=incident.severity,
        status=incident.status,
        commander_id=incident.commander_id,
        created_by_id=incident.created_by_id,
        declared_at=incident.declared_at,
        resolved_at=incident.resolved_at,
        version=incident.version,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        services=services,
        role_assignments=roles,
    )


def serialize_timeline(db: Session, event) -> TimelineEventOut:
    actor = db.get(User, event.actor_id) if event.actor_id else None
    return TimelineEventOut(
        id=event.id,
        incident_id=event.incident_id,
        event_type=event.event_type,
        message=event.message,
        metadata=event.metadata_,
        actor_id=event.actor_id,
        created_at=event.created_at,
        actor_username=actor.username if actor else None,
    )


def serialize_action_item(db: Session, item) -> ActionItemOut:
    assignee = db.get(User, item.assignee_id) if item.assignee_id else None
    return ActionItemOut(
        id=item.id,
        incident_id=item.incident_id,
        title=item.title,
        description=item.description,
        assignee_id=item.assignee_id,
        status=item.status,
        due_at=item.due_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        assignee_username=assignee.username if assignee else None,
    )
