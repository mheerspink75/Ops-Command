"""Seed demonstration data.

Creates a demo organization, users for each role, services and dependencies,
an active incident, a resolved incident, a sample playbook, and timeline /
action-item data. Idempotent: safe to run multiple times.

Demonstration credentials are intentionally non-production and documented in
the README.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.incident import (
    ActionItem,
    Incident,
    IncidentRoleAssignment,
    IncidentService,
    TimelineEvent,
)
from app.db.models.organization import Membership, Organization
from app.db.models.playbook import Playbook
from app.db.models.service import Service, ServiceDependency
from app.db.models.user import User
from app.db.session import session_scope
from app.security.passwords import hash_password

DEMO_PASSWORD = "Demo-Password-123!"  # non-production, documented in README


def _get_or_create_user(session: Session, email: str, username: str) -> User:
    user = session.query(User).filter(func.lower(User.email) == email.lower()).first()
    if user is None:
        user = User(email=email, username=username, password_hash=hash_password(DEMO_PASSWORD))
        session.add(user)
        session.flush()
    return user


def seed() -> None:
    with session_scope() as session:
        # --- Organization ---
        org = session.query(Organization).filter(Organization.slug == "acme-ops").first()
        if org is None:
            org = Organization(name="Acme Operations", slug="acme-ops")
            session.add(org)
            session.flush()

        # --- Users (one per role) ---
        owner = _get_or_create_user(session, "owner@acme-ops.io", "demo-owner")
        admin = _get_or_create_user(session, "admin@acme-ops.io", "demo-admin")
        responder = _get_or_create_user(session, "responder@acme-ops.io", "demo-responder")
        viewer = _get_or_create_user(session, "viewer@acme-ops.io", "demo-viewer")

        for user, role in [
            (owner, "owner"),
            (admin, "administrator"),
            (responder, "responder"),
            (viewer, "viewer"),
        ]:
            existing = (
                session.query(Membership)
                .filter(Membership.user_id == user.id, Membership.organization_id == org.id)
                .first()
            )
            if existing is None:
                session.add(Membership(user_id=user.id, organization_id=org.id, role=role))

        # --- Services ---
        def svc(name: str, tier: str) -> Service:
            s = (
                session.query(Service)
                .filter(Service.organization_id == org.id, Service.name == name)
                .first()
            )
            if s is None:
                s = Service(organization_id=org.id, name=name, tier=tier, status="active")
                session.add(s)
                session.flush()
            return s

        api = svc("checkout-api", "critical")
        db = svc("orders-database", "critical")
        cache = svc("session-cache", "standard")
        queue = svc("event-queue", "standard")

        # --- Dependencies ---
        deps = [
            (api.id, db.id, "sync"),
            (api.id, cache.id, "sync"),
            (api.id, queue.id, "async"),
        ]
        for up, down, dtype in deps:
            exists = (
                session.query(ServiceDependency)
                .filter(
                    ServiceDependency.upstream_service_id == up,
                    ServiceDependency.downstream_service_id == down,
                    ServiceDependency.dependency_type == dtype,
                )
                .first()
            )
            if exists is None:
                session.add(
                    ServiceDependency(
                        upstream_service_id=up,
                        downstream_service_id=down,
                        dependency_type=dtype,
                    )
                )

        # --- Active incident ---
        active = (
            session.query(Incident)
            .filter(Incident.organization_id == org.id, Incident.title == "Checkout latency spike")
            .first()
        )
        if active is None:
            active = Incident(
                organization_id=org.id,
                title="Checkout latency spike",
                summary="P99 checkout latency above SLO since 14:00 UTC.",
                severity="SEV2",
                status="investigating",
                commander_id=owner.id,
                created_by_id=responder.id,
                version=2,
            )
            session.add(active)
            session.flush()
            session.add(IncidentService(incident_id=active.id, service_id=api.id))
            session.add(IncidentService(incident_id=active.id, service_id=db.id))
            session.add(
                IncidentRoleAssignment(incident_id=active.id, user_id=owner.id, role="commander")
            )
            session.add(
                IncidentRoleAssignment(
                    incident_id=active.id, user_id=responder.id, role="operations"
                )
            )
            session.add(
                TimelineEvent(
                    incident_id=active.id,
                    event_type="declared",
                    message="Incident declared: Checkout latency spike",
                    metadata_={"severity": "SEV2"},
                    actor_id=responder.id,
                )
            )
            session.add(
                TimelineEvent(
                    incident_id=active.id,
                    event_type="status_change",
                    message="Status changed from declared to investigating",
                    metadata_={"from": "declared", "to": "investigating"},
                    actor_id=owner.id,
                )
            )
            session.add(
                ActionItem(
                    incident_id=active.id,
                    title="Check database connection pool",
                    description="Verify pool saturation on orders-database.",
                    assignee_id=responder.id,
                    status="in_progress",
                )
            )

        # --- Resolved incident ---
        resolved = (
            session.query(Incident)
            .filter(Incident.organization_id == org.id, Incident.title == "Cache eviction storm")
            .first()
        )
        if resolved is None:
            resolved = Incident(
                organization_id=org.id,
                title="Cache eviction storm",
                summary="Mass cache evictions caused a thundering herd.",
                severity="SEV3",
                status="resolved",
                commander_id=admin.id,
                created_by_id=admin.id,
                version=5,
            )
            session.add(resolved)
            session.flush()
            session.add(IncidentService(incident_id=resolved.id, service_id=cache.id))
            session.add(
                TimelineEvent(
                    incident_id=resolved.id,
                    event_type="declared",
                    message="Incident declared: Cache eviction storm",
                    metadata_={"severity": "SEV3"},
                    actor_id=admin.id,
                )
            )
            session.add(
                TimelineEvent(
                    incident_id=resolved.id,
                    event_type="status_change",
                    message="Status changed from monitoring to resolved",
                    metadata_={"from": "monitoring", "to": "resolved"},
                    actor_id=admin.id,
                )
            )
            session.add(
                ActionItem(
                    incident_id=resolved.id,
                    title="Add jitter to cache TTLs",
                    description="Prevent synchronized expirations.",
                    assignee_id=responder.id,
                    status="done",
                )
            )

        # --- Playbook ---
        playbook = (
            session.query(Playbook)
            .filter(Playbook.organization_id == org.id, Playbook.name == "Standard escalation")
            .first()
        )
        if playbook is None:
            playbook = Playbook(
                organization_id=org.id,
                name="Standard escalation",
                description="A sample escalation playbook for demonstration.",
                enabled=True,
                steps=[
                    {"type": "timeline_message", "params": {"message": "Escalation started"}},
                    {
                        "type": "create_action_item",
                        "params": {"title": "Notify on-call", "status": "open"},
                    },
                    {"type": "change_status", "params": {"status": "investigating"}},
                    {"type": "wait", "params": {"seconds": 1}},
                    {"type": "snapshot", "params": {}},
                ],
            )
            session.add(playbook)

        session.commit()
        print("Seed complete.")
        print(f"  Organization: {org.name} ({org.slug})")
        print(f"  Users: owner, admin, responder, viewer (password: {DEMO_PASSWORD})")
        print(f"  Services: {api.name}, {db.name}, {cache.name}, {queue.name}")
        print(f"  Active incident: {active.title}")
        print(f"  Resolved incident: {resolved.title}")
        print(f"  Playbook: {playbook.name}")


if __name__ == "__main__":
    seed()
