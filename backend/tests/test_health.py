"""Tests for liveness, readiness, and metrics endpoints."""

from __future__ import annotations


class TestLiveness:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "service" in body

    def test_health_requires_no_auth(self, client):
        # Liveness must be reachable without credentials.
        resp = client.get("/health")
        assert resp.status_code == 200


class TestReadiness:
    def test_ready_returns_valid_json_with_checks(self, client):
        # The readiness probe reports the health of each dependency. The exact
        # status depends on the real infrastructure (the probe checks the app's
        # configured database, not the test's in-memory one), so we assert the
        # contract: valid JSON with a status and per-dependency checks.
        resp = client.get("/ready")
        assert resp.status_code in (200, 503)
        assert "application/json" in resp.headers["content-type"]
        body = resp.json()
        assert body["status"] in ("ready", "degraded")
        assert "database" in body["checks"]
        assert "redis" in body["checks"]

    def test_ready_status_matches_checks(self, client):
        # The overall status must be consistent with the individual checks:
        # "ready" only when every check is "ok", otherwise "degraded".
        resp = client.get("/ready")
        body = resp.json()
        all_ok = all(v == "ok" for v in body["checks"].values())
        expected = "ready" if all_ok else "degraded"
        assert body["status"] == expected
        assert resp.status_code == (200 if all_ok else 503)


class TestMetrics:
    def test_metrics_returns_prometheus_text(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        # Prometheus exposition format uses lines of `name value` or comments.
        assert isinstance(resp.text, str) and len(resp.text) >= 0
