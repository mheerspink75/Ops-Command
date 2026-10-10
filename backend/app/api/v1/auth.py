"""Authentication endpoints: register, login, refresh, logout, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import ConflictError, UnauthorizedError
from app.db.models.user import User
from app.db.session import get_db
from app.observability.logging import get_logger
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from app.security import throttle
from app.security.auth import get_current_user
from app.security.passwords import hash_password, verify_password
from app.services import token_service

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _token_pair(access: str, refresh: str) -> TokenPair:
    settings = get_settings()
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_ttl_seconds,
    )


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    existing = (
        db.query(User)
        .filter(
            (func.lower(User.email) == payload.email.lower())
            | (func.lower(User.username) == payload.username.lower())
        )
        .first()
    )
    if existing is not None:
        raise ConflictError("A user with that email or username already exists")
    user = User(
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("user.registered", extra={"username": user.username})
    return user


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenPair:
    identifier = payload.email
    throttle.check_or_raise(identifier)

    user = db.query(User).filter(func.lower(User.email) == payload.email.lower()).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        throttle.record_login_failure(identifier)
        logger.warning("auth.login_failed", extra={"identifier": identifier})
        raise UnauthorizedError("Invalid email or password")
    if not user.active:
        raise UnauthorizedError("Account is disabled")

    access, refresh = token_service.issue_tokens(db, user)
    throttle.clear_login_throttle(identifier)
    logger.info("auth.login_success", extra={"username": user.username})
    return _token_pair(access, refresh)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    access, new_refresh = token_service.rotate_refresh(db, payload.refresh_token)
    return _token_pair(access, new_refresh)


@router.post("/logout", status_code=204)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)) -> None:
    token_service.revoke_refresh(db, payload.refresh_token)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
