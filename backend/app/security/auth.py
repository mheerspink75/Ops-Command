"""FastAPI authentication and organization-scoped authorization dependencies.

Authorization is enforced server-side. The frontend is never a security
boundary. Every org-scoped route resolves the caller's membership and role
before any data is returned.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, Path
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError, UnauthorizedError
from app.db.models.organization import Membership, Organization
from app.db.models.user import User
from app.db.session import get_db
from app.security.tokens import decode_access_token

# Higher number = more privilege.
ROLE_HIERARCHY: dict[str, int] = {
    "viewer": 1,
    "responder": 2,
    "administrator": 3,
    "owner": 4,
}


@dataclass(frozen=True)
class OrgContext:
    user: User
    org: Organization
    membership: Membership

    @property
    def role(self) -> str:
        return self.membership.role

    def has_role(self, min_role: str) -> bool:
        return ROLE_HIERARCHY.get(self.role, 0) >= ROLE_HIERARCHY.get(min_role, 99)


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired access token") from exc
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.active:
        raise UnauthorizedError("User not found or inactive")
    return user


def get_org_context(
    org_id: uuid.UUID = Path(..., description="Organization id"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrgContext:
    """Resolve the caller's membership in the target organization.

    Raises 404 if the org does not exist and 403 if the caller is not a member.
    This prevents cross-organization access via identifiers in the URL.
    """
    org = db.get(Organization, org_id)
    if org is None:
        raise NotFoundError("Organization not found")
    membership = (
        db.query(Membership)
        .filter(Membership.user_id == user.id, Membership.organization_id == org_id)
        .first()
    )
    if membership is None:
        raise ForbiddenError("Not a member of this organization")
    return OrgContext(user=user, org=org, membership=membership)


def require_role(min_role: str):
    """Return a dependency that enforces a minimum role within the org."""

    def dependency(ctx: OrgContext = Depends(get_org_context)) -> OrgContext:
        if not ctx.has_role(min_role):
            raise ForbiddenError(f"Requires role '{min_role}' or higher; you have '{ctx.role}'")
        return ctx

    return dependency
