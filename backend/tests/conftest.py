"""Shared test fixtures: isolated database, test client, seeded users."""

from __future__ import annotations

import os
from datetime import UTC, datetime

# Use a proper-length signing key for tests (>= 32 bytes for HS256) so we don't
# rely on the insecure dev default. Must be set before app settings are read
# (get_settings is lru_cached), hence before the app imports below.
os.environ.setdefault("SECRET_KEY", "test-only-signing-key-0123456789-0123456789-0123456789")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.incident import Incident
from app.db.models.organization import Membership, Organization
from app.db.models.playbook import Playbook
from app.db.models.service import Service
from app.db.models.user import User
from app.db.session import get_db
from app.main import app
from app.security.passwords import hash_password

TEST_DATABASE_URL = "sqlite:///./test_opscommand.db"


@pytest.fixture()
def engine():
    """Create a fresh in-memory SQLite database for each test.

    Function-scoped so every test starts from a clean slate. The application
    code commits its own transactions, which would otherwise leak state into
    subsequent tests sharing a session-scoped database.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def _clear_login_throttle():
    """Clear login-throttle state before each test.

    Throttling is backed by a shared Redis (see app.security.throttle). Without
    this, a test that trips the throttle (e.g. the failed-login test) would
    leak state into subsequent tests, causing spurious 429s on their logins.
    """
    from app.core.redis_client import get_redis

    r = get_redis()
    for key in r.scan_iter("login_throttle:*"):
        r.delete(key)
    yield


@pytest.fixture()
def db_session(engine):
    """Provide a transactional test session with rollback."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session, engine):
    """FastAPI test client with the test database injected."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Also override the session factory used by WebSocket and worker code.
    import app.db.session as db_session_module

    original_factory = db_session_module._session_factory

    test_factory = sessionmaker(bind=engine)
    db_session_module._session_factory = test_factory

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    db_session_module._session_factory = original_factory


@pytest.fixture()
def org(db_session) -> Organization:
    o = Organization(name="Test Org", slug="test-org")
    db_session.add(o)
    db_session.flush()
    return o


@pytest.fixture()
def owner_user(db_session, org) -> User:
    u = User(
        email="owner@test.io",
        username="test-owner",
        password_hash=hash_password("Test-Pass-123!"),
        active=True,
    )
    db_session.add(u)
    db_session.flush()
    db_session.add(Membership(user_id=u.id, organization_id=org.id, role="owner"))
    db_session.flush()
    return u


@pytest.fixture()
def responder_user(db_session, org) -> User:
    u = User(
        email="responder@test.io",
        username="test-responder",
        password_hash=hash_password("Test-Pass-123!"),
        active=True,
    )
    db_session.add(u)
    db_session.flush()
    db_session.add(Membership(user_id=u.id, organization_id=org.id, role="responder"))
    db_session.flush()
    return u


@pytest.fixture()
def viewer_user(db_session, org) -> User:
    u = User(
        email="viewer@test.io",
        username="test-viewer",
        password_hash=hash_password("Test-Pass-123!"),
        active=True,
    )
    db_session.add(u)
    db_session.flush()
    db_session.add(Membership(user_id=u.id, organization_id=org.id, role="viewer"))
    db_session.flush()
    return u


@pytest.fixture()
def other_org(db_session) -> Organization:
    o = Organization(name="Other Org", slug="other-org")
    db_session.add(o)
    db_session.flush()
    return o


@pytest.fixture()
def other_org_user(db_session, other_org) -> User:
    u = User(
        email="other@test.io",
        username="test-other",
        password_hash=hash_password("Test-Pass-123!"),
        active=True,
    )
    db_session.add(u)
    db_session.flush()
    db_session.add(Membership(user_id=u.id, organization_id=other_org.id, role="owner"))
    db_session.flush()
    return u


@pytest.fixture()
def service(db_session, org) -> Service:
    s = Service(
        organization_id=org.id,
        name="test-service",
        tier="critical",
        status="active",
    )
    db_session.add(s)
    db_session.flush()
    return s


@pytest.fixture()
def incident(db_session, org, owner_user, responder_user, service) -> Incident:
    i = Incident(
        organization_id=org.id,
        title="Test Incident",
        summary="A test incident",
        severity="SEV2",
        status="declared",
        commander_id=owner_user.id,
        created_by_id=responder_user.id,
        declared_at=datetime.now(UTC),
        version=1,
    )
    db_session.add(i)
    db_session.flush()
    return i


@pytest.fixture()
def playbook(db_session, org) -> Playbook:
    p = Playbook(
        organization_id=org.id,
        name="Test Playbook",
        description="A test playbook",
        enabled=True,
        steps=[
            {"type": "timeline_message", "params": {"message": "Playbook started"}},
            {"type": "wait", "params": {"seconds": 0.1}},
        ],
    )
    db_session.add(p)
    db_session.flush()
    return p


def _login(client: TestClient, email: str, password: str) -> dict:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def owner_token(client, owner_user) -> str:
    data = _login(client, "owner@test.io", "Test-Pass-123!")
    return data["access_token"]


@pytest.fixture()
def responder_token(client, responder_user) -> str:
    data = _login(client, "responder@test.io", "Test-Pass-123!")
    return data["access_token"]


@pytest.fixture()
def viewer_token(client, viewer_user) -> str:
    data = _login(client, "viewer@test.io", "Test-Pass-123!")
    return data["access_token"]


@pytest.fixture()
def other_org_token(client, other_org_user) -> str:
    data = _login(client, "other@test.io", "Test-Pass-123!")
    return data["access_token"]
