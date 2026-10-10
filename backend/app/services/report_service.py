"""Post-incident report generation from persisted data.

Only facts present in the incident record are included. Missing information is
explicitly marked as incomplete. No facts are invented.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.models.incident import Incident
from app.db.models.user import User

INCOMPLETE = "_Incomplete — to be completed by the incident commander._"


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "unknown"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _duration(declared_at: datetime, resolved_at: datetime | None) -> str:
    if resolved_at is None:
        return "Ongoing (not yet resolved)"
    delta = resolved_at - declared_at
    total_seconds = int(delta.total_seconds())
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def generate_report(session: Session, *, incident_id: uuid.UUID, org_id: uuid.UUID) -> str:
    incident = (
        session.query(Incident)
        .filter(Incident.id == incident_id, Incident.organization_id == org_id)
        .first()
    )
    if incident is None:
        raise NotFoundError("Incident not found")

    # Eager-load relationships.
    services = [isv.service for isv in incident.services]
    assignments = incident.role_assignments
    timeline = sorted(incident.timeline, key=lambda e: e.created_at)
    action_items = sorted(incident.action_items, key=lambda a: a.created_at)

    # Resolve usernames for responders and actors.
    user_ids = {a.user_id for a in assignments}
    user_ids.update(e.actor_id for e in timeline if e.actor_id)
    users: dict[uuid.UUID, User] = {}
    if user_ids:
        for u in session.query(User).filter(User.id.in_(user_ids)).all():
            users[u.id] = u

    def uname(uid: uuid.UUID | None) -> str:
        if uid is None:
            return "system"
        u = users.get(uid)
        return u.username if u else str(uid)

    lines: list[str] = []
    lines.append(f"# Post-Incident Report: {incident.title}")
    lines.append("")
    lines.append(f"- **Incident ID:** `{incident.id}`")
    lines.append(f"- **Severity:** {incident.severity}")
    lines.append(f"- **Final status:** {incident.status}")
    lines.append(f"- **Declared at:** {_fmt_dt(incident.declared_at)}")
    lines.append(f"- **Resolved at:** {_fmt_dt(incident.resolved_at)}")
    lines.append(f"- **Duration:** {_duration(incident.declared_at, incident.resolved_at)}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(incident.summary if incident.summary else INCOMPLETE)
    lines.append("")

    lines.append("## Impacted Services")
    lines.append("")
    if services:
        for s in services:
            lines.append(f"- {s.name} (tier: {s.tier}, status: {s.status})")
    else:
        lines.append(INCOMPLETE)
    lines.append("")

    lines.append("## Responders and Roles")
    lines.append("")
    if assignments:
        for a in assignments:
            lines.append(f"- {uname(a.user_id)} — {a.role}")
    else:
        lines.append(INCOMPLETE)
    lines.append("")

    lines.append("## Timeline")
    lines.append("")
    if timeline:
        for e in timeline:
            lines.append(
                f"- **{_fmt_dt(e.created_at)}** [{e.event_type}] {e.message} — {uname(e.actor_id)}"
            )
    else:
        lines.append(INCOMPLETE)
    lines.append("")

    lines.append("## Root Cause")
    lines.append("")
    lines.append(INCOMPLETE)
    lines.append("")

    lines.append("## Resolution")
    lines.append("")
    if incident.resolved_at is not None:
        lines.append(f"Resolved at {_fmt_dt(incident.resolved_at)}.")
        # Use the last timeline event before resolution as context if present.
    else:
        lines.append("Incident has not been resolved yet.")
    lines.append("")

    lines.append("## Follow-up Action Items")
    lines.append("")
    if action_items:
        for item in action_items:
            assignee = uname(item.assignee_id) if item.assignee_id else "unassigned"
            lines.append(f"- [{item.status}] {item.title} (assignee: {assignee})")
    else:
        lines.append(INCOMPLETE)
    lines.append("")

    lines.append("## Lessons Learned")
    lines.append("")
    lines.append(INCOMPLETE)
    lines.append("")

    lines.append("---")
    lines.append(f"_Report generated at {_fmt_dt(datetime.now(UTC))} by OpsCommand._")
    lines.append("")

    return "\n".join(lines)
