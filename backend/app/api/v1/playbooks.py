"""Playbook and playbook-run endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.db.models.playbook import Playbook, PlaybookRun
from app.db.session import get_db
from app.realtime.hub import hub
from app.schemas.playbook import (
    PlaybookCreate,
    PlaybookOut,
    PlaybookRunOut,
    PlaybookRunStart,
)
from app.security.auth import OrgContext, get_org_context, require_role
from app.services import playbook_service
from app.worker.tasks import dispatch_playbook_run

router_playbooks = APIRouter(prefix="/organizations/{org_id}/playbooks", tags=["playbooks"])
router_runs = APIRouter(
    prefix="/organizations/{org_id}/incidents/{incident_id}/playbook-runs",
    tags=["playbook-runs"],
)


@router_playbooks.post("", response_model=PlaybookOut, status_code=201)
def create_playbook(
    payload: PlaybookCreate,
    request: Request,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(require_role("administrator")),
) -> Playbook:
    playbook = Playbook(
        organization_id=ctx.org.id,
        name=payload.name,
        description=payload.description,
        enabled=payload.enabled,
        steps=[s.model_dump() for s in payload.steps],
    )
    db.add(playbook)
    db.commit()
    db.refresh(playbook)
    return playbook


@router_playbooks.get("", response_model=list[PlaybookOut])
def list_playbooks(
    db: Session = Depends(get_db), ctx: OrgContext = Depends(get_org_context)
) -> list[Playbook]:
    return (
        db.query(Playbook)
        .filter(Playbook.organization_id == ctx.org.id)
        .order_by(Playbook.created_at)
        .all()
    )


@router_runs.post("", response_model=PlaybookRunOut, status_code=202)
def start_run(
    incident_id: uuid.UUID,
    payload: PlaybookRunStart,
    request: Request,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(require_role("responder")),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> PlaybookRun:
    key = idempotency_key or payload.idempotency_key or uuid.uuid4().hex
    run, created = playbook_service.start_run(
        db,
        incident_id=incident_id,
        org_id=ctx.org.id,
        playbook_id=payload.playbook_id,
        idempotency_key=key,
    )
    if created:
        dispatch_playbook_run(str(run.id))
        hub.publish(str(incident_id), {"type": "playbook_started", "run_id": str(run.id)})
    return run


@router_runs.get("", response_model=list[PlaybookRunOut])
def list_runs(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(get_org_context),
) -> list[PlaybookRun]:
    return (
        db.query(PlaybookRun)
        .filter(PlaybookRun.incident_id == incident_id)
        .order_by(PlaybookRun.created_at.desc())
        .all()
    )


@router_runs.get("/{run_id}", response_model=PlaybookRunOut)
def get_run(
    incident_id: uuid.UUID,
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(get_org_context),
) -> PlaybookRun:
    run = (
        db.query(PlaybookRun)
        .filter(PlaybookRun.id == run_id, PlaybookRun.incident_id == incident_id)
        .first()
    )
    if run is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Playbook run not found")
    return run
