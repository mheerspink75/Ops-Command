"""Tests for playbook creation and run idempotency.

`dispatch_playbook_run` is patched so the tests are deterministic and can assert
exactly when the worker task is enqueued (once on creation, never on a
duplicate idempotency key).
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

from app.db.models.playbook import Playbook


class TestPlaybookCreation:
    def test_create_playbook(self, client, org, owner_token):
        resp = client.post(
            f"/api/v1/organizations/{org.id}/playbooks",
            json={
                "name": "My Playbook",
                "description": "desc",
                "enabled": True,
                "steps": [{"type": "timeline_message", "params": {"message": "hi"}}],
            },
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "My Playbook"
        assert body["enabled"] is True
        assert len(body["steps"]) == 1

    def test_create_playbook_requires_admin(self, client, org, responder_token):
        resp = client.post(
            f"/api/v1/organizations/{org.id}/playbooks",
            json={"name": "Nope", "steps": []},
            headers={"Authorization": f"Bearer {responder_token}"},
        )
        assert resp.status_code == 403

    def test_list_playbooks(self, client, org, owner_token, playbook):
        resp = client.get(
            f"/api/v1/organizations/{org.id}/playbooks",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 200
        assert "Test Playbook" in [p["name"] for p in resp.json()]


class TestPlaybookRunIdempotency:
    def test_start_run_returns_202_and_dispatches(
        self, client, org, responder_token, incident, playbook
    ):
        with patch("app.api.v1.playbooks.dispatch_playbook_run") as mock_dispatch:
            resp = client.post(
                f"/api/v1/organizations/{org.id}/incidents/{incident.id}/playbook-runs",
                json={"playbook_id": str(playbook.id), "idempotency_key": "key-1"},
                headers={"Authorization": f"Bearer {responder_token}"},
            )
        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "pending"
        assert body["idempotency_key"] == "key-1"
        mock_dispatch.assert_called_once_with(body["id"])

    def test_duplicate_key_returns_same_run_without_redispatch(
        self, client, org, responder_token, incident, playbook
    ):
        with patch("app.api.v1.playbooks.dispatch_playbook_run") as mock_dispatch:
            resp1 = client.post(
                f"/api/v1/organizations/{org.id}/incidents/{incident.id}/playbook-runs",
                json={"playbook_id": str(playbook.id), "idempotency_key": "key-dup"},
                headers={"Authorization": f"Bearer {responder_token}"},
            )
            resp2 = client.post(
                f"/api/v1/organizations/{org.id}/incidents/{incident.id}/playbook-runs",
                json={"playbook_id": str(playbook.id), "idempotency_key": "key-dup"},
                headers={"Authorization": f"Bearer {responder_token}"},
            )
        assert resp1.status_code == 202
        assert resp2.status_code == 202
        assert resp1.json()["id"] == resp2.json()["id"]
        # Dispatched exactly once (on creation), not again for the duplicate.
        assert mock_dispatch.call_count == 1

    def test_different_key_creates_new_run(self, client, org, responder_token, incident, playbook):
        with patch("app.api.v1.playbooks.dispatch_playbook_run"):
            resp1 = client.post(
                f"/api/v1/organizations/{org.id}/incidents/{incident.id}/playbook-runs",
                json={"playbook_id": str(playbook.id), "idempotency_key": "key-a"},
                headers={"Authorization": f"Bearer {responder_token}"},
            )
            resp2 = client.post(
                f"/api/v1/organizations/{org.id}/incidents/{incident.id}/playbook-runs",
                json={"playbook_id": str(playbook.id), "idempotency_key": "key-b"},
                headers={"Authorization": f"Bearer {responder_token}"},
            )
        assert resp1.json()["id"] != resp2.json()["id"]

    def test_idempotency_key_from_header(self, client, org, responder_token, incident, playbook):
        with patch("app.api.v1.playbooks.dispatch_playbook_run"):
            resp = client.post(
                f"/api/v1/organizations/{org.id}/incidents/{incident.id}/playbook-runs",
                json={"playbook_id": str(playbook.id)},
                headers={
                    "Authorization": f"Bearer {responder_token}",
                    "Idempotency-Key": "header-key",
                },
            )
        assert resp.status_code == 202
        assert resp.json()["idempotency_key"] == "header-key"

    def test_disabled_playbook_rejected(self, client, org, responder_token, incident, db_session):
        disabled = Playbook(
            organization_id=org.id,
            name="Disabled",
            enabled=False,
            steps=[{"type": "timeline_message", "params": {"message": "x"}}],
        )
        db_session.add(disabled)
        db_session.flush()
        resp = client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/playbook-runs",
            json={"playbook_id": str(disabled.id), "idempotency_key": "key-disabled"},
            headers={"Authorization": f"Bearer {responder_token}"},
        )
        assert resp.status_code == 403

    def test_missing_playbook_404(self, client, org, responder_token, incident):
        resp = client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/playbook-runs",
            json={"playbook_id": str(uuid.uuid4()), "idempotency_key": "key-missing"},
            headers={"Authorization": f"Bearer {responder_token}"},
        )
        assert resp.status_code == 404

    def test_start_run_requires_responder(self, client, org, viewer_token, incident, playbook):
        with patch("app.api.v1.playbooks.dispatch_playbook_run"):
            resp = client.post(
                f"/api/v1/organizations/{org.id}/incidents/{incident.id}/playbook-runs",
                json={"playbook_id": str(playbook.id), "idempotency_key": "key-viewer"},
                headers={"Authorization": f"Bearer {viewer_token}"},
            )
        assert resp.status_code == 403

    def test_list_runs(self, client, org, responder_token, incident, playbook):
        with patch("app.api.v1.playbooks.dispatch_playbook_run"):
            client.post(
                f"/api/v1/organizations/{org.id}/incidents/{incident.id}/playbook-runs",
                json={"playbook_id": str(playbook.id), "idempotency_key": "key-list"},
                headers={"Authorization": f"Bearer {responder_token}"},
            )
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/playbook-runs",
            headers={"Authorization": f"Bearer {responder_token}"},
        )
        assert resp.status_code == 200
        assert any(r["idempotency_key"] == "key-list" for r in resp.json())

    def test_get_run(self, client, org, responder_token, incident, playbook):
        with patch("app.api.v1.playbooks.dispatch_playbook_run"):
            run_id = client.post(
                f"/api/v1/organizations/{org.id}/incidents/{incident.id}/playbook-runs",
                json={"playbook_id": str(playbook.id), "idempotency_key": "key-get"},
                headers={"Authorization": f"Bearer {responder_token}"},
            ).json()["id"]
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/playbook-runs/{run_id}",
            headers={"Authorization": f"Bearer {responder_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == run_id
