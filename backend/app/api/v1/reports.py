"""Post-incident report endpoints (Markdown preview and download)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.report import ReportOut
from app.security.auth import OrgContext, get_org_context
from app.services import report_service

router = APIRouter(
    prefix="/organizations/{org_id}/incidents/{incident_id}/report",
    tags=["reports"],
)


@router.get("", response_model=ReportOut)
def get_report(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(get_org_context),
) -> ReportOut:
    content = report_service.generate_report(db, incident_id=incident_id, org_id=ctx.org.id)
    return ReportOut(
        incident_id=incident_id,
        generated_at=datetime.now(UTC),
        content=content,
    )


@router.get("/download")
def download_report(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(get_org_context),
) -> Response:
    content = report_service.generate_report(db, incident_id=incident_id, org_id=ctx.org.id)
    filename = f"incident-{incident_id}-report.md"
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
