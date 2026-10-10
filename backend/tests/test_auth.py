"""Tests for authentication: registration, login, refresh rotation, revocation, throttling."""

from __future__ import annotations


class TestRegistration:
    def test_register_new_user(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.io",
                "username": "newuser",
                "password": "Strong-Pass-123!",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "newuser@test.io"
        assert body["username"] == "newuser"
        assert "password" not in body

    def test_register_duplicate_email_rejected(self, client, owner_user):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "owner@test.io",
                "username": "different-name",
                "password": "Strong-Pass-123!",
            },
        )
        assert resp.status_code == 409

    def test_register_duplicate_username_rejected(self, client, owner_user):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "different@test.io",
                "username": "test-owner",
                "password": "Strong-Pass-123!",
            },
        )
        assert resp.status_code == 409


class TestLogin:
    def test_login_success(self, client, owner_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@test.io", "password": "Test-Pass-123!"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    def test_login_wrong_password(self, client, owner_user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@test.io", "password": "Wrong-Pass-123!"},
        )
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@test.io", "password": "Test-Pass-123!"},
        )
        assert resp.status_code == 401

    def test_login_inactive_user(self, client, owner_user):
        owner_user.active = False
        owner_user._sa_instance_state.session.commit()  # type: ignore[attr-defined]
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@test.io", "password": "Test-Pass-123!"},
        )
        assert resp.status_code == 401


class TestRefreshRotation:
    def test_refresh_returns_new_tokens(self, client, owner_user):
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@test.io", "password": "Test-Pass-123!"},
        ).json()
        old_refresh = login["refresh_token"]

        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"]
        assert body["refresh_token"] != old_refresh

    def test_refresh_token_cannot_be_reused(self, client, owner_user):
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@test.io", "password": "Test-Pass-123!"},
        ).json()
        refresh = login["refresh_token"]

        # First rotation succeeds.
        resp1 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert resp1.status_code == 200

        # Replaying the old token must fail.
        resp2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert resp2.status_code == 401

    def test_refresh_with_invalid_token(self, client):
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not-a-real-token"},
        )
        assert resp.status_code == 401


class TestLogout:
    def test_logout_revokes_refresh_token(self, client, owner_user):
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@test.io", "password": "Test-Pass-123!"},
        ).json()
        refresh = login["refresh_token"]

        resp = client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
        assert resp.status_code == 204

        # The revoked token can no longer be used.
        resp2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert resp2.status_code == 401


class TestMe:
    def test_me_returns_current_user(self, client, owner_user, owner_token):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "owner@test.io"
        assert body["username"] == "test-owner"

    def test_me_without_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token(self, client):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 401


class TestThrottling:
    def test_login_throttled_after_max_failures(self, client, owner_user):
        """After 5 failed logins, the 6th should be throttled (429)."""
        for _ in range(5):
            client.post(
                "/api/v1/auth/login",
                json={"email": "owner@test.io", "password": "Wrong-Pass-123!"},
            )
        # The 6th attempt should be throttled.
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@test.io", "password": "Test-Pass-123!"},
        )
        assert resp.status_code == 429
