"""Tests for WebSocket authentication, unauthorized subscriptions, and real-time publication.

Rejection cases assert that the socket is closed before any message is sent
(the client therefore never receives a ``connected`` handshake). Publication
cases assert that an event published to the incident room reaches a connected
client. The Redis bridge may deliver an event more than once, so publication
tests accept the first matching event rather than requiring exactly one.
"""

from __future__ import annotations

import uuid

import pytest
from starlette.websockets import WebSocketDisconnect

WS_PATH = "/api/v1/ws/incidents/{incident_id}"


class TestWebSocketAuth:
    def test_valid_token_connects(self, client, org, owner_token, incident):
        with client.websocket_connect(
            WS_PATH.format(incident_id=incident.id) + f"?token={owner_token}"
        ) as ws:
            msg = ws.receive_json()
            assert msg["type"] == "connected"
            assert msg["incident_id"] == str(incident.id)

    def test_responder_token_also_connects(self, client, org, responder_token, incident):
        with client.websocket_connect(
            WS_PATH.format(incident_id=incident.id) + f"?token={responder_token}"
        ) as ws:
            assert ws.receive_json()["type"] == "connected"

    def test_invalid_token_rejected(self, client, org, incident):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                WS_PATH.format(incident_id=incident.id) + "?token=not-a-valid-token"
            ) as ws:
                ws.receive_json()

    def test_missing_token_rejected(self, client, org, incident):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(WS_PATH.format(incident_id=incident.id)) as ws:
                ws.receive_json()

    def test_non_member_rejected(self, client, org, other_org, other_org_token, incident):
        # Valid token, but the user is not a member of the incident's org.
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                WS_PATH.format(incident_id=incident.id) + f"?token={other_org_token}"
            ) as ws:
                ws.receive_json()

    def test_unknown_incident_rejected(self, client, org, owner_token):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                WS_PATH.format(incident_id=uuid.uuid4()) + f"?token={owner_token}"
            ) as ws:
                ws.receive_json()


class TestRealtimePublication:
    def test_published_event_reaches_connected_client(self, client, org, owner_token, incident):
        from app.realtime.hub import hub

        with client.websocket_connect(
            WS_PATH.format(incident_id=incident.id) + f"?token={owner_token}"
        ) as ws:
            # Handshake first (subscription is registered before this is sent).
            assert ws.receive_json()["type"] == "connected"

            hub.publish(str(incident.id), {"type": "test_event", "payload": "hello"})

            delivered = False
            for _ in range(5):
                msg = ws.receive_json()
                if msg.get("type") == "test_event":
                    assert msg["payload"] == "hello"
                    delivered = True
                    break
            assert delivered, "published event was not delivered to the client"

    def test_events_are_scoped_to_incident(self, org, incident, db_session):
        """Publishing to a different incident must not leak into this room."""
        from app.db.models.incident import Incident
        from app.realtime.hub import hub

        # A second incident in the same org.
        other = Incident(
            organization_id=org.id,
            title="Other Incident",
            severity="SEV3",
            status="declared",
            created_by_id=incident.created_by_id,
            version=1,
        )
        db_session.add(other)
        db_session.flush()

        received: list = []

        def callback(event):
            received.append(event)

        hub.subscribe(str(incident.id), callback)
        try:
            # Publishing to a different room must not reach this room's subscriber.
            hub.publish(str(other.id), {"type": "other_room_event"})
            assert received == []
        finally:
            hub.unsubscribe(str(incident.id), callback)
