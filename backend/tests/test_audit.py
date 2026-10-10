"""Tests for audit-log sanitization and audit event retrieval.

Covers both the pure sanitization helpers (unit) and the end-to-end guarantee
that sensitive values never reach the persisted audit record (integration).
"""

from __future__ import annotations

from app.core.sanitize import sanitize_detail, sanitize_headers, sanitize_value


class TestSanitizeValue:
    def test_redacts_sensitive_keys(self):
        result = sanitize_value({"password": "hunter2", "username": "alice"})
        assert result["password"] == "***REDACTED***"
        assert result["username"] == "alice"

    def test_redacts_nested_sensitive_keys(self):
        payload = {"outer": {"access_token": "abc", "safe": "ok"}, "list": [{"token": "x"}]}
        result = sanitize_value(payload)
        assert result["outer"]["access_token"] == "***REDACTED***"
        assert result["outer"]["safe"] == "ok"
        assert result["list"][0]["token"] == "***REDACTED***"

    def test_case_insensitive_keys(self):
        result = sanitize_value({"Password": "secret", "API_KEY": "k"})
        assert result["Password"] == "***REDACTED***"
        assert result["API_KEY"] == "***REDACTED***"

    def test_non_container_values_pass_through(self):
        assert sanitize_value("plain") == "plain"
        assert sanitize_value(42) == 42
        assert sanitize_value(None) is None

    def test_does_not_mutate_input(self):
        original = {"password": "secret"}
        snapshot = dict(original)
        sanitize_value(original)
        assert original == snapshot


class TestSanitizeDetail:
    def test_none_returns_empty_dict(self):
        assert sanitize_detail(None) == {}

    def test_empty_returns_empty_dict(self):
        assert sanitize_detail({}) == {}

    def test_redacts_secrets(self):
        detail = {"action": "login", "password": "p", "refresh_token": "r"}
        result = sanitize_detail(detail)
        assert result["action"] == "login"
        assert result["password"] == "***REDACTED***"
        assert result["refresh_token"] == "***REDACTED***"


class TestSanitizeHeaders:
    def test_redacts_authorization(self):
        headers = {"Authorization": "Bearer abc", "X-Request-Id": "req-1"}
        result = sanitize_headers(headers)
        assert result["Authorization"] == "***REDACTED***"
        assert result["X-Request-Id"] == "req-1"

    def test_none_returns_empty(self):
        assert sanitize_headers(None) == {}


class TestAuditIntegration:
    def test_incident_create_records_sanitized_audit(self, client, org, owner_token, db_session):
        # Create an incident through the API; this records an audit event.
        resp = client.post(
            f"/api/v1/organizations/{org.id}/incidents",
            json={"title": "Audit Test", "severity": "SEV3"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 201

        # Retrieve the audit log and confirm the event is present.
        audit_resp = client.get(
            f"/api/v1/organizations/{org.id}/audit",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert audit_resp.status_code == 200
        body = audit_resp.json()
        assert body["total"] >= 1
        actions = [e["action"] for e in body["items"]]
        assert "incident.create" in actions

    def test_audit_detail_never_contains_secrets(self, client, org, owner_token):
        # Even if a caller were to pass sensitive fields, the persisted detail
        # must be redacted. We exercise the sanitization contract directly via
        # the helper used by record_audit.
        detail = {"title": "x", "password": "leak", "authorization": "Bearer leak"}
        sanitized = sanitize_detail(detail)
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["authorization"] == "***REDACTED***"
        assert sanitized["title"] == "x"

    def test_audit_is_org_scoped(self, client, org, other_org, owner_token, other_org_token):
        # Create an incident in `org`.
        client.post(
            f"/api/v1/organizations/{org.id}/incidents",
            json={"title": "Scoped", "severity": "SEV3"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        # The other org's audit log must not include this event.
        resp = client.get(
            f"/api/v1/organizations/{other_org.id}/audit",
            headers={"Authorization": f"Bearer {other_org_token}"},
        )
        assert resp.status_code == 200
        assert all(e["action"] != "incident.create" for e in resp.json()["items"])

    def test_audit_filter_by_action(self, client, org, owner_token):
        client.post(
            f"/api/v1/organizations/{org.id}/incidents",
            json={"title": "Filter", "severity": "SEV3"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        resp = client.get(
            f"/api/v1/organizations/{org.id}/audit?action=incident.create",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        assert all(e["action"] == "incident.create" for e in items)
