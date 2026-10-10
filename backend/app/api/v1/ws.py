"""Authenticated WebSocket endpoint for incident rooms.

Clients connect to /ws/incidents/{incident_id}?token=<access_token>. The
connection is authorized at connect time (membership + org check) and cleaned
up on disconnect. Heartbeats use the WebSocket ping/pong protocol.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.db.models.incident import Incident
from app.db.models.organization import Membership
from app.db.models.user import User
from app.db.session import get_session_factory
from app.observability.metrics import set_ws_connections
from app.realtime.hub import hub
from app.security.tokens import decode_access_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


def _authorize(token: str, incident_id: uuid.UUID) -> bool:
    """Verify the token and that the user may access this incident's org."""
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        return False
    if payload.get("type") != "access":
        return False
    user_id = uuid.UUID(payload["sub"])

    factory = get_session_factory()
    with factory() as session:
        incident = session.query(Incident).filter(Incident.id == incident_id).first()
        if incident is None:
            return False
        user = session.get(User, user_id)
        if user is None or not user.active:
            return False
        membership = (
            session.query(Membership)
            .filter(
                Membership.user_id == user_id,
                Membership.organization_id == incident.organization_id,
            )
            .first()
        )
        return membership is not None


@router.websocket("/ws/incidents/{incident_id}")
async def incident_room(
    websocket: WebSocket,
    incident_id: uuid.UUID,
    token: str = Query(default=""),
) -> None:
    if not _authorize(token, incident_id):
        # Reject unauthorized subscriptions before accepting the socket.
        await websocket.close(code=4401, reason="unauthorized")
        return

    await websocket.accept()
    incident_key = str(incident_id)
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict] = asyncio.Queue()

    def _on_event(event: dict) -> None:
        # Called from the hub (possibly another thread); schedule onto the loop.
        loop.call_soon_threadsafe(queue.put_nowait, event)

    hub.subscribe(incident_key, _on_event)
    set_ws_connections(hub.connection_count)
    try:
        await websocket.send_json({"type": "connected", "incident_id": incident_key})
        while True:
            # Wait for either an inbound client message or an outbound event.
            try:
                message = await asyncio.wait_for(queue.get(), timeout=25)
                await websocket.send_json(message)
            except TimeoutError:
                # Application-level heartbeat to keep the connection alive.
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("websocket error for incident %s", incident_key)
    finally:
        hub.unsubscribe(incident_key, _on_event)
        set_ws_connections(hub.connection_count)
