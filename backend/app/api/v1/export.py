"""Incident JSON export endpoint."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.v1.serializers import (
    serialize_action_item,
    serialize_incident,
    serialize_timeline,
)
from app.db.session import get_db
from app.security.auth import OrgContext, get_org_context
from app.services import incident_service

router = APIRouter(
    prefix="/organizations/{org_id}/incidents/{incident_id}/export",
    tags=["export"],
)


@router.get("")
def export_incident(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(get_org_context),
) -> Response:
    incident = incident_service._load_incident(db, incident_id, ctx.org.id)
    payload = {
        "incident": serialize_incident(db, incident).model_dump(mode="json"),
        "timeline": [
            serialize_timeline(db, e).model_dump(mode="json")
            for e in sorted(incident.timeline, key=lambda x: x.created_at)
        ],
        "action_items": [
            serialize_action_item(db, i).model_dump(mode="json")
            for i in sorted(incident.action_items, key=lambda x: x.created_at)
        ],
    }
    return Response(
        content=json.dumps(payload, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="incident-{incident_id}.json"'},
    )
