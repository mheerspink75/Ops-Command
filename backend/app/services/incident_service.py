"""Incident lifecycle service.

Enforces valid status transitions, optimistic concurrency (via a conditional
UPDATE on the version column), and produces timeline + audit events atomically
with each mutation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session, selectinload

from app.core.audit import record_audit
from app.core.errors import (
    ConcurrencyError,
    ForbiddenError,
    InvalidTransitionError,
    NotFoundError,
)
from app.db.models.incident import (
    ActionItem,
    Incident,
    IncidentRoleAssignment,
    IncidentService,
    TimelineEvent,
)
from app.db.models.service import Service
from app.db.models.user import User

# Valid status transitions (forward chain + documented recovery paths).
VALID_TRANSITIONS: dict[str, set[str]] = {
    "declared": {"investigating"},
    "investigating": {"identified"},
    "identified": {"monitoring", "investigating"},
    "monitoring": {"resolved", "investigating"},
    "resolved": {"closed"},
    "closed": set(),
}

SEVERITIES = {"SEV1", "SEV2", "SEV3", "SEV4"}
STATUSES = set(VALID_TRANSITIONS.keys())
ROLES = {"commander", "communications", "operations", "scribe"}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _load_incident(session: Session, incident_id: uuid.UUID, org_id: uuid.UUID) -> Incident:
    incident = session.execute(
        select(Incident)
        .options(
            selectinload(Incident.services),
            selectinload(Incident.timeline),
            selectinload(Incident.role_assignments),
            selectinload(Incident.action_items),
        )
        .where(Incident.id == incident_id, Incident.organization_id == org_id)
    ).scalar_one_or_none()
    if incident is None:
        # 404 (not 403) to avoid leaking existence across organizations.
        raise NotFoundError("Incident not found")
    return incident


def create_incident(
    session: Session,
    *,
    org_id: uuid.UUID,
    actor: User,
    title: str,
    summary: str | None,
    severity: str,
    service_ids: list[uuid.UUID],
    commander_id: uuid.UUID | None,
    request_id: str | None = None,
) -> Incident:
    if severity not in SEVERITIES:
        raise InvalidTransitionError(f"Invalid severity: {severity}")

    # Validate services belong to the org (prevents cross-org attachment).
    if service_ids:
        found = (
            session.query(Service.id)
            .filter(Service.id.in_(service_ids), Service.organization_id == org_id)
            .all()
        )
        if len(found) != len(set(service_ids)):
            raise ForbiddenError("One or more services do not belong to this organization")

    incident = Incident(
        organization_id=org_id,
        title=title,
        summary=summary,
        severity=severity,
        status="declared",
        commander_id=commander_id,
        created_by_id=actor.id,
        declared_at=_utcnow(),
        version=1,
    )
    session.add(incident)
    session.flush()

    for sid in set(service_ids):
        session.add(IncidentService(incident_id=incident.id, service_id=sid))

    if commander_id:
        session.add(
            IncidentRoleAssignment(incident_id=incident.id, user_id=commander_id, role="commander")
        )

    session.add(
        TimelineEvent(
            incident_id=incident.id,
            event_type="declared",
            message=f"Incident declared: {title}",
            metadata_={"severity": severity},
            actor_id=actor.id,
            created_at=_utcnow(),
        )
    )

    record_audit(
        session,
        organization_id=org_id,
        actor_id=actor.id,
        action="incident.create",
        resource_type="incident",
        resource_id=incident.id,
        detail={"title": title, "severity": severity},
        request_id=request_id,
    )
    session.commit()
    session.refresh(incident)
    return incident


def transition_status(
    session: Session,
    *,
    incident_id: uuid.UUID,
    org_id: uuid.UUID,
    actor: User | None,
    new_status: str,
    expected_version: int | None,
    request_id: str | None = None,
) -> Incident:
    incident = _load_incident(session, incident_id, org_id)
    old_status = incident.status

    if new_status not in STATUSES:
        raise InvalidTransitionError(f"Unknown status: {new_status}")
    if new_status not in VALID_TRANSITIONS.get(old_status, set()):
        raise InvalidTransitionError(f"Invalid transition from '{old_status}' to '{new_status}'")

    base_version = expected_version if expected_version is not None else incident.version
    now = _utcnow()
    values: dict[str, Any] = {
        "status": new_status,
        "version": base_version + 1,
        "updated_at": now,
    }
    if new_status == "resolved":
        values["resolved_at"] = now

    result = session.execute(
        update(Incident)
        .where(Incident.id == incident_id, Incident.version == base_version)
        .values(**values)
    )
    if cast(CursorResult, result).rowcount == 0:
        raise ConcurrencyError("Incident was modified by another responder. Reload and retry.")

    session.add(
        TimelineEvent(
            incident_id=incident_id,
            event_type="status_change",
            message=f"Status changed from {old_status} to {new_status}",
            metadata_={"from": old_status, "to": new_status},
            actor_id=actor.id if actor else None,
            created_at=now,
        )
    )
    record_audit(
        session,
        organization_id=org_id,
        actor_id=actor.id if actor else None,
        action="incident.status_change",
        resource_type="incident",
        resource_id=incident_id,
        detail={"from": old_status, "to": new_status},
        request_id=request_id,
    )
    session.commit()
    return _load_incident(session, incident_id, org_id)


def update_incident(
    session: Session,
    *,
    incident_id: uuid.UUID,
    org_id: uuid.UUID,
    actor: User,
    title: str | None,
    summary: str | None,
    severity: str | None,
    service_ids: list[uuid.UUID] | None,
    commander_id: uuid.UUID | None,
    expected_version: int | None,
    request_id: str | None = None,
) -> Incident:
    incident = _load_incident(session, incident_id, org_id)
    base_version = expected_version if expected_version is not None else incident.version

    if severity is not None and severity not in SEVERITIES:
        raise InvalidTransitionError(f"Invalid severity: {severity}")

    values: dict[str, Any] = {"version": base_version + 1, "updated_at": _utcnow()}
    changes: dict[str, Any] = {}
    if title is not None:
        values["title"] = title
        changes["title"] = title
    if summary is not None:
        values["summary"] = summary
        changes["summary"] = summary
    if severity is not None and severity != incident.severity:
        changes["severity"] = {"from": incident.severity, "to": severity}
        values["severity"] = severity
    if commander_id is not None:
        values["commander_id"] = commander_id
        changes["commander_id"] = str(commander_id)

    result = session.execute(
        update(Incident)
        .where(Incident.id == incident_id, Incident.version == base_version)
        .values(**values)
    )
    if cast(CursorResult, result).rowcount == 0:
        raise ConcurrencyError("Incident was modified by another responder. Reload and retry.")

    if service_ids is not None:
        if service_ids:
            found = (
                session.query(Service.id)
                .filter(Service.id.in_(service_ids), Service.organization_id == org_id)
                .all()
            )
            if len(found) != len(set(service_ids)):
                raise ForbiddenError("One or more services do not belong to this organization")
        session.query(IncidentService).filter(IncidentService.incident_id == incident_id).delete()
        for sid in set(service_ids):
            session.add(IncidentService(incident_id=incident_id, service_id=sid))

    if changes:
        session.add(
            TimelineEvent(
                incident_id=incident_id,
                event_type="updated",
                message="Incident details updated",
                metadata_=changes,
                actor_id=actor.id,
                created_at=_utcnow(),
            )
        )
        record_audit(
            session,
            organization_id=org_id,
            actor_id=actor.id,
            action="incident.update",
            resource_type="incident",
            resource_id=incident_id,
            detail=changes,
            request_id=request_id,
        )
    session.commit()
    return _load_incident(session, incident_id, org_id)


def add_timeline_event(
    session: Session,
    *,
    incident_id: uuid.UUID,
    org_id: uuid.UUID,
    actor: User | None,
    event_type: str,
    message: str,
    metadata: dict | None,
    request_id: str | None = None,
) -> TimelineEvent:
    _load_incident(session, incident_id, org_id)
    event = TimelineEvent(
        incident_id=incident_id,
        event_type=event_type,
        message=message,
        metadata_=metadata,
        actor_id=actor.id if actor else None,
        created_at=_utcnow(),
    )
    session.add(event)
    record_audit(
        session,
        organization_id=org_id,
        actor_id=actor.id if actor else None,
        action="timeline.add",
        resource_type="timeline_event",
        resource_id=incident_id,
        detail={"event_type": event_type},
        request_id=request_id,
    )
    session.commit()
    session.refresh(event)
    return event


def assign_role(
    session: Session,
    *,
    incident_id: uuid.UUID,
    org_id: uuid.UUID,
    actor: User,
    user_id: uuid.UUID,
    role: str,
    request_id: str | None = None,
) -> IncidentRoleAssignment:
    incident = _load_incident(session, incident_id, org_id)
    if role not in ROLES:
        raise InvalidTransitionError(f"Invalid role: {role}")

    # The assigned user must be a member of the org.
    from app.db.models.organization import Membership

    membership = (
        session.query(Membership)
        .filter(Membership.user_id == user_id, Membership.organization_id == org_id)
        .first()
    )
    if membership is None:
        raise ForbiddenError("Assigned user is not a member of this organization")

    existing = (
        session.query(IncidentRoleAssignment)
        .filter(
            IncidentRoleAssignment.incident_id == incident_id,
            IncidentRoleAssignment.user_id == user_id,
        )
        .first()
    )
    if existing is not None:
        existing.role = role
        existing.assigned_at = _utcnow()
        assignment = existing
    else:
        assignment = IncidentRoleAssignment(
            incident_id=incident_id, user_id=user_id, role=role, assigned_at=_utcnow()
        )
        session.add(assignment)

    if role == "commander":
        incident.commander_id = user_id

    session.add(
        TimelineEvent(
            incident_id=incident_id,
            event_type="role_assignment",
            message=f"Role '{role}' assigned",
            metadata_={"role": role, "user_id": str(user_id)},
            actor_id=actor.id,
            created_at=_utcnow(),
        )
    )
    record_audit(
        session,
        organization_id=org_id,
        actor_id=actor.id,
        action="incident.assign_role",
        resource_type="incident",
        resource_id=incident_id,
        detail={"role": role, "user_id": str(user_id)},
        request_id=request_id,
    )
    session.commit()
    session.refresh(assignment)
    return assignment


def create_action_item(
    session: Session,
    *,
    incident_id: uuid.UUID,
    org_id: uuid.UUID,
    actor: User | None,
    title: str,
    description: str | None,
    assignee_id: uuid.UUID | None,
    status: str,
    due_at: datetime | None,
    request_id: str | None = None,
) -> ActionItem:
    _load_incident(session, incident_id, org_id)
    item = ActionItem(
        incident_id=incident_id,
        title=title,
        description=description,
        assignee_id=assignee_id,
        status=status,
        due_at=due_at,
    )
    session.add(item)
    session.flush()
    session.add(
        TimelineEvent(
            incident_id=incident_id,
            event_type="action_item",
            message=f"Action item created: {title}",
            metadata_={"action_item_id": str(item.id)},
            actor_id=actor.id if actor else None,
            created_at=_utcnow(),
        )
    )
    record_audit(
        session,
        organization_id=org_id,
        actor_id=actor.id if actor else None,
        action="action_item.create",
        resource_type="action_item",
        resource_id=item.id,
        detail={"title": title},
        request_id=request_id,
    )
    session.commit()
    session.refresh(item)
    return item


def update_action_item(
    session: Session,
    *,
    incident_id: uuid.UUID,
    org_id: uuid.UUID,
    actor: User,
    item_id: uuid.UUID,
    title: str | None,
    description: str | None,
    assignee_id: uuid.UUID | None,
    status: str | None,
    due_at: datetime | None,
    request_id: str | None = None,
) -> ActionItem:
    _load_incident(session, incident_id, org_id)
    item = (
        session.query(ActionItem)
        .filter(ActionItem.id == item_id, ActionItem.incident_id == incident_id)
        .first()
    )
    if item is None:
        raise NotFoundError("Action item not found")

    if title is not None:
        item.title = title
    if description is not None:
        item.description = description
    if assignee_id is not None:
        item.assignee_id = assignee_id
    if status is not None:
        item.status = status
    if due_at is not None:
        item.due_at = due_at

    record_audit(
        session,
        organization_id=org_id,
        actor_id=actor.id,
        action="action_item.update",
        resource_type="action_item",
        resource_id=item.id,
        detail={"status": status},
        request_id=request_id,
    )
    session.commit()
    session.refresh(item)
    return item


def search_incidents(
    session: Session,
    *,
    org_id: uuid.UUID,
    status: str | None,
    severity: str | None,
    q: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Incident], int]:
    query = select(Incident).where(Incident.organization_id == org_id)
    if status:
        query = query.where(Incident.status == status)
    if severity:
        query = query.where(Incident.severity == severity)
    if q:
        like = f"%{q}%"
        query = query.where(Incident.title.ilike(like) | Incident.summary.ilike(like))

    total = session.execute(select(func.count()).select_from(query.subquery())).scalar_one()

    rows = (
        session.execute(query.order_by(Incident.created_at.desc()).limit(limit).offset(offset))
        .scalars()
        .all()
    )
    return list(rows), int(total)
