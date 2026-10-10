"""Tests for incident JSON export."""

from __future__ import annotations


class TestIncidentExport:
    def test_export_returns_incident_payload(self, client, org, owner_token, incident):
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/export",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "incident" in body
        assert "timeline" in body
        assert "action_items" in body
        assert body["incident"]["id"] == str(incident.id)
        assert body["incident"]["title"] == "Test Incident"

    def test_export_includes_timeline_and_action_items(self, client, org, owner_token, incident):
        # Add a timeline event and an action item.
        client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/timeline",
            json={"message": "Exported event", "event_type": "update"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/action-items",
            json={"title": "Exported item", "status": "open"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/export",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        body = resp.json()
        assert any(e["message"] == "Exported event" for e in body["timeline"])
        assert any(i["title"] == "Exported item" for i in body["action_items"])

    def test_export_sets_attachment_header(self, client, org, owner_token, incident):
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/export",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert f"incident-{incident.id}.json" in resp.headers["content-disposition"]

    def test_export_requires_membership(self, client, org, other_org, other_org_token, incident):
        # A user from another org cannot export this incident.
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/export",
            headers={"Authorization": f"Bearer {other_org_token}"},
        )
        assert resp.status_code in (403, 404)

    def test_export_missing_incident_404(self, client, org, owner_token):
        import uuid

        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents/{uuid.uuid4()}/export",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 404
