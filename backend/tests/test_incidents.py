"""Tests for incident lifecycle: creation, transitions, concurrency, timeline."""

from __future__ import annotations


class TestIncidentCreation:
    def test_create_incident(self, client, org, owner_token, service):
        resp = client.post(
            f"/api/v1/organizations/{org.id}/incidents",
            json={
                "title": "New Incident",
                "summary": "Something broke",
                "severity": "SEV1",
                "service_ids": [str(service.id)],
            },
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "New Incident"
        assert body["severity"] == "SEV1"
        assert body["status"] == "declared"
        assert body["version"] == 1

    def test_create_incident_requires_responder_role(self, client, org, viewer_token):
        resp = client.post(
            f"/api/v1/organizations/{org.id}/incidents",
            json={"title": "Nope", "severity": "SEV3"},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_create_incident_invalid_severity(self, client, org, owner_token):
        resp = client.post(
            f"/api/v1/organizations/{org.id}/incidents",
            json={"title": "Bad", "severity": "SEV99"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 422

    def test_create_incident_cross_org_service_rejected(self, client, org, other_org, owner_token):
        from app.db.models.service import Service

        # Create a service in the other org.
        other_svc = Service(
            organization_id=other_org.id,
            name="other-svc",
            tier="standard",
            status="active",
        )
        # We need to add it to the db session.
        # Use the client to get a db session.
        # Actually, let's just use the fixture approach.
        # For this test, we'll create the service directly.
        from app.db.session import get_session_factory

        factory = get_session_factory()
        with factory() as session:
            session.add(other_svc)
            session.commit()
            other_svc_id = other_svc.id

        resp = client.post(
            f"/api/v1/organizations/{org.id}/incidents",
            json={
                "title": "Cross-org",
                "severity": "SEV2",
                "service_ids": [str(other_svc_id)],
            },
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 403


class TestStatusTransitions:
    def test_valid_transition_declared_to_investigating(self, client, org, owner_token, incident):
        resp = client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/status",
            json={"status": "investigating", "expected_version": 1},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "investigating"
        assert resp.json()["version"] == 2

    def test_valid_full_lifecycle(self, client, org, owner_token, incident):
        transitions = [
            ("investigating", 1),
            ("identified", 2),
            ("monitoring", 3),
            ("resolved", 4),
            ("closed", 5),
        ]
        for status, version in transitions:
            resp = client.post(
                f"/api/v1/organizations/{org.id}/incidents/{incident.id}/status",
                json={"status": status, "expected_version": version},
                headers={"Authorization": f"Bearer {owner_token}"},
            )
            assert resp.status_code == 200, f"Transition to {status} failed: {resp.text}"
            assert resp.json()["status"] == status

    def test_invalid_transition_declared_to_resolved(self, client, org, owner_token, incident):
        resp = client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/status",
            json={"status": "resolved", "expected_version": 1},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 422

    def test_invalid_transition_closed_to_anything(self, client, org, owner_token, incident):
        # First transition to closed.
        for status, version in [
            ("investigating", 1),
            ("identified", 2),
            ("monitoring", 3),
            ("resolved", 4),
            ("closed", 5),
        ]:
            client.post(
                f"/api/v1/organizations/{org.id}/incidents/{incident.id}/status",
                json={"status": status, "expected_version": version},
                headers={"Authorization": f"Bearer {owner_token}"},
            )
        # Now try to transition from closed.
        resp = client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/status",
            json={"status": "investigating", "expected_version": 6},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 422

    def test_recovery_transition_monitoring_to_investigating(
        self, client, org, owner_token, incident
    ):
        # Get to monitoring.
        for status, version in [("investigating", 1), ("identified", 2), ("monitoring", 3)]:
            client.post(
                f"/api/v1/organizations/{org.id}/incidents/{incident.id}/status",
                json={"status": status, "expected_version": version},
                headers={"Authorization": f"Bearer {owner_token}"},
            )
        # Recovery: monitoring -> investigating.
        resp = client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/status",
            json={"status": "investigating", "expected_version": 4},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "investigating"


class TestOptimisticConcurrency:
    def test_stale_version_rejected(self, client, org, owner_token, incident):
        # First update succeeds.
        resp1 = client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/status",
            json={"status": "investigating", "expected_version": 1},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp1.status_code == 200

        # Second update with the same (now stale) version should fail.
        resp2 = client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/status",
            json={"status": "identified", "expected_version": 1},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp2.status_code == 409


class TestTimeline:
    def test_add_timeline_event(self, client, org, owner_token, incident):
        resp = client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/timeline",
            json={"message": "Investigating root cause", "event_type": "update"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["message"] == "Investigating root cause"
        assert body["event_type"] == "update"

    def test_list_timeline(self, client, org, owner_token, incident):
        # Add an event.
        client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/timeline",
            json={"message": "Test event", "event_type": "update"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/timeline",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        items = body["items"]
        assert len(items) >= 1
        assert any(e["message"] == "Test event" for e in items)


class TestRoleAssignment:
    def test_assign_role(self, client, org, owner_token, incident, responder_user):
        resp = client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/roles",
            json={"user_id": str(responder_user.id), "role": "operations"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["role"] == "operations"
        assert body["user_id"] == str(responder_user.id)

    def test_assign_role_non_member_rejected(
        self, client, org, owner_token, incident, other_org_user
    ):
        resp = client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/roles",
            json={"user_id": str(other_org_user.id), "role": "operations"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 403

    def test_list_roles(self, client, org, owner_token, incident):
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/roles",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 200
        roles = resp.json()
        assert isinstance(roles, list)


class TestActionItems:
    def test_create_action_item(self, client, org, owner_token, incident):
        resp = client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/action-items",
            json={
                "title": "Fix the bug",
                "description": "Details here",
                "status": "open",
            },
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Fix the bug"
        assert body["status"] == "open"

    def test_update_action_item_status(self, client, org, owner_token, incident):
        # Create first.
        create_resp = client.post(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/action-items",
            json={"title": "Task", "status": "open"},
            headers={"Authorization": f"Bearer {owner_token}"},
        ).json()
        item_id = create_resp["id"]

        resp = client.patch(
            f"/api/v1/organizations/{org.id}/incidents/{incident.id}/action-items/{item_id}",
            json={"status": "done"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "done"


class TestIncidentSearch:
    def test_list_incidents(self, client, org, owner_token, incident):
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 1

    def test_filter_by_status(self, client, org, owner_token, incident):
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents?status=declared",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert all(i["status"] == "declared" for i in body["items"])

    def test_filter_by_severity(self, client, org, owner_token, incident):
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents?severity=SEV2",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert all(i["severity"] == "SEV2" for i in body["items"])


class TestOrganizationIsolation:
    def test_cannot_access_other_org_incident(
        self, client, org, other_org, owner_token, other_org_token, incident
    ):
        # The other org's user should not be able to see this incident.
        resp = client.get(
            f"/api/v1/organizations/{other_org.id}/incidents/{incident.id}",
            headers={"Authorization": f"Bearer {other_org_token}"},
        )
        assert resp.status_code == 404

    def test_cannot_list_other_org_incidents(
        self, client, org, other_org, owner_token, other_org_token, incident
    ):
        resp = client.get(
            f"/api/v1/organizations/{other_org.id}/incidents",
            headers={"Authorization": f"Bearer {other_org_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        # The incident belongs to `org`, not `other_org`, so it should not appear.
        assert all(i["id"] != str(incident.id) for i in body["items"])

    def test_non_member_cannot_access_org(self, client, org, other_org_user):
        # other_org_user is not a member of `org`.
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents",
            headers={"Authorization": f"Bearer {other_org_user and ''}"},
        )
        # This will fail auth since we don't have a valid token for this user in this org.
        # Let's use the other_org_token instead.
        from tests.conftest import _login

        token = _login(client, "other@test.io", "Test-Pass-123!")["access_token"]
        resp = client.get(
            f"/api/v1/organizations/{org.id}/incidents",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
