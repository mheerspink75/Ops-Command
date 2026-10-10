"""Refresh-token issuance, rotation, and revocation.

Only SHA-256 hashes of refresh tokens are stored. Rotation revokes the old
session and links it to its replacement (replay of a rotated token is rejected).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import UnauthorizedError
from app.db.models.token import TokenSession
from app.db.models.user import User
from app.security.tokens import (
    create_access_token,
    generate_refresh_token,
    hash_token,
    refresh_token_ttl,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(dt: datetime) -> datetime:
    """Normalize a stored timestamp to an aware UTC datetime.

    SQLite returns naive datetimes even for ``DateTime(timezone=True)`` columns,
    so treat naive values as UTC to keep comparisons safe across backends.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def issue_tokens(session: Session, user: User) -> tuple[str, str]:
    access = create_access_token(user.id, user.username)
    refresh = generate_refresh_token()
    session.add(
        TokenSession(
            user_id=user.id,
            token_hash=hash_token(refresh),
            expires_at=_now() + refresh_token_ttl(),
        )
    )
    session.commit()
    return access, refresh


def rotate_refresh(session: Session, refresh_token: str) -> tuple[str, str]:
    token_hash = hash_token(refresh_token)
    ts = session.query(TokenSession).filter(TokenSession.token_hash == token_hash).first()
    if ts is None:
        raise UnauthorizedError("Invalid refresh token")
    if ts.revoked:
        # A rotated token being replayed: revoke the whole chain for safety.
        _revoke_chain(session, ts)
        raise UnauthorizedError("Refresh token already used")
    if _as_utc(ts.expires_at) < _now():
        raise UnauthorizedError("Refresh token expired")

    user = session.get(User, ts.user_id)
    if user is None or not user.active:
        raise UnauthorizedError("User not found or inactive")

    new_refresh = generate_refresh_token()
    new_ts = TokenSession(
        user_id=user.id,
        token_hash=hash_token(new_refresh),
        expires_at=_now() + refresh_token_ttl(),
    )
    session.add(new_ts)
    session.flush()
    ts.revoked = True
    ts.replaced_by = new_ts.id

    access = create_access_token(user.id, user.username)
    session.commit()
    return access, new_refresh


def revoke_refresh(session: Session, refresh_token: str) -> None:
    token_hash = hash_token(refresh_token)
    ts = session.query(TokenSession).filter(TokenSession.token_hash == token_hash).first()
    if ts is not None and not ts.revoked:
        ts.revoked = True
        session.commit()


def _revoke_chain(session: Session, ts: TokenSession) -> None:
    """Revoke this session and any session it was replaced by (replay defense)."""
    seen: set[uuid.UUID] = set()
    current: TokenSession | None = ts
    while current is not None and current.id not in seen:
        seen.add(current.id)
        if not current.revoked:
            current.revoked = True
        if current.replaced_by is None:
            break
        current = session.get(TokenSession, current.replaced_by)
