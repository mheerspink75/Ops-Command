"""Tests for post-incident report generation."""

from __future__ import annotations

import uuid


class TestReportGeneration:
    def test_report_returns_markdown(self, client, org, owner_token, incident):
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/report",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["incident_id"] == str(incident.id)
        assert "generated_at" in body
        assert body["content"].startswith("# Post-Incident Report")

    def test_report_contains_core_sections(self, client, org, owner_token, incident):
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/report",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        content = resp.json()["content"]
        for section in [
            "## Summary",
            "## Impacted Services",
            "## Responders and Roles",
            "## Timeline",
            "## Root Cause",
            "## Resolution",
            "## Follow-up Action Items",
            "## Lessons Learned",
        ]:
            assert section in content, f"Missing section: {section}"

    def test_report_marks_missing_data_incomplete(self, client, org, owner_token, incident):
        # A freshly declared incident has no timeline, responders, or action items.
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/report",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        content = resp.json()["content"]
        assert "Incomplete" in content

    def test_report_includes_timeline_when_present(self, client, org, owner_token, incident):
        client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/timeline",
            json={"message": "Report timeline entry", "event_type": "update"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/report",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert "Report timeline entry" in resp.json()["content"]

    def test_report_download_returns_markdown_attachment(self, client, org, owner_token, incident):
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/report/download",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]
        assert f"incident-{incident.id}-report.md" in resp.headers["content-disposition"]

    def test_report_requires_membership(self, client, org, other_org, other_org_token, incident):
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/report",
            headers={"Authorization": f"Bearer {other_org_token}"},
        )
        assert resp.status_code in (403, 404)

    def test_report_missing_incident_404(self, client, org, owner_token):
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents/{uuid.uuid4()}/report",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 404
