"""Organization and membership endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.errors import ForbiddenError, NotFoundError
from app.db.models.organization import Membership, Organization
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.org import (
    InviteMemberRequest,
    MembershipOut,
    OrganizationCreate,
    OrganizationOut,
)
from app.security.auth import OrgContext, get_current_user, get_org_context, require_role
from app.services import org_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _membership_out(m: Membership, user: User | None) -> MembershipOut:
    return MembershipOut(
        user_id=m.user_id,
        organization_id=m.organization_id,
        role=m.role,
        created_at=m.created_at,
        username=user.username if user else None,
        email=user.email if user else None,
    )


@router.post("", response_model=OrganizationOut, status_code=201)
def create_organization(
    payload: OrganizationCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Organization:
    org = org_service.create_organization(
        db,
        name=payload.name,
        slug=payload.slug,
        owner=user,
        request_id=request.headers.get("X-Request-ID"),
    )
    return org


@router.get("", response_model=list[OrganizationOut])
def list_my_organizations(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Organization]:
    org_ids = [
        m.organization_id for m in db.query(Membership).filter(Membership.user_id == user.id).all()
    ]
    if not org_ids:
        return []
    return (
        db.query(Organization)
        .filter(Organization.id.in_(org_ids))
        .order_by(Organization.created_at)
        .all()
    )


@router.get("/{org_id}", response_model=OrganizationOut)
def get_organization(ctx: OrgContext = Depends(get_org_context)) -> Organization:
    return ctx.org


@router.get("/{org_id}/members", response_model=list[MembershipOut])
def list_members(
    db: Session = Depends(get_db), ctx: OrgContext = Depends(get_org_context)
) -> list[MembershipOut]:
    memberships = org_service.list_memberships(db, org=ctx.org)
    users = {
        u.id: u for u in db.query(User).filter(User.id.in_([m.user_id for m in memberships])).all()
    }
    return [_membership_out(m, users.get(m.user_id)) for m in memberships]


@router.post("/{org_id}/members", response_model=MembershipOut, status_code=201)
def invite_member(
    payload: InviteMemberRequest,
    request: Request,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(require_role("administrator")),
) -> MembershipOut:
    membership = org_service.invite_member(
        db,
        org=ctx.org,
        inviter=ctx.user,
        email=payload.email,
        role=payload.role,
        request_id=request.headers.get("X-Request-ID"),
    )
    target = db.get(User, membership.user_id)
    return _membership_out(membership, target)


@router.delete("/{org_id}/members/{user_id}", status_code=204)
def remove_member(
    user_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(require_role("administrator")),
) -> None:
    if user_id == ctx.user.id and ctx.role != "owner":
        raise ForbiddenError("You cannot remove yourself")
    membership = org_service.get_membership(db, org=ctx.org, user_id=user_id)
    if membership is None:
        raise NotFoundError("Member not found")
    db.delete(membership)
    record_audit(
        db,
        organization_id=ctx.org.id,
        actor_id=ctx.user.id,
        action="membership.remove",
        resource_type="membership",
        resource_id=str(user_id),
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()
