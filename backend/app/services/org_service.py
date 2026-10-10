"""Organization and membership operations."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.errors import ConflictError, NotFoundError
from app.db.models.organization import Membership, Organization
from app.db.models.user import User


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


def create_organization(
    session: Session,
    *,
    name: str,
    slug: str | None,
    owner: User,
    request_id: str | None = None,
) -> Organization:
    base_slug = slug or slugify(name)
    candidate = base_slug
    n = 1
    while (
        session.query(Organization.id)
        .filter(func.lower(Organization.slug) == candidate.lower())
        .first()
        is not None
    ):
        n += 1
        candidate = f"{base_slug}-{n}"

    org = Organization(name=name, slug=candidate)
    session.add(org)
    session.flush()

    membership = Membership(user_id=owner.id, organization_id=org.id, role="owner")
    session.add(membership)

    record_audit(
        session,
        organization_id=org.id,
        actor_id=owner.id,
        action="organization.create",
        resource_type="organization",
        resource_id=org.id,
        detail={"name": name, "slug": candidate},
        request_id=request_id,
    )
    session.commit()
    session.refresh(org)
    return org


def invite_member(
    session: Session,
    *,
    org: Organization,
    inviter: User,
    email: str,
    role: str,
    request_id: str | None = None,
) -> Membership:
    target = session.query(User).filter(func.lower(User.email) == email.lower()).first()
    if target is None:
        raise NotFoundError("No user with that email exists. Ask them to register first.")

    existing = (
        session.query(Membership)
        .filter(
            Membership.user_id == target.id,
            Membership.organization_id == org.id,
        )
        .first()
    )
    if existing is not None:
        raise ConflictError("User is already a member of this organization")

    membership = Membership(user_id=target.id, organization_id=org.id, role=role)
    session.add(membership)

    record_audit(
        session,
        organization_id=org.id,
        actor_id=inviter.id,
        action="membership.invite",
        resource_type="membership",
        resource_id=str(target.id),
        detail={"email": email, "role": role},
        request_id=request_id,
    )
    session.commit()
    session.refresh(membership)
    return membership


def list_memberships(session: Session, *, org: Organization) -> list[Membership]:
    return (
        session.query(Membership)
        .filter(Membership.organization_id == org.id)
        .order_by(Membership.created_at)
        .all()
    )


def get_membership(session: Session, *, org: Organization, user_id: uuid.UUID) -> Membership | None:
    return (
        session.query(Membership)
        .filter(
            Membership.user_id == user_id,
            Membership.organization_id == org.id,
        )
        .first()
    )
