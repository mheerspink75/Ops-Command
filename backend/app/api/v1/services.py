"""Service and service-dependency endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.errors import ConflictError, NotFoundError
from app.db.models.service import Service, ServiceDependency
from app.db.session import get_db
from app.schemas.service import (
    ServiceCreate,
    ServiceDependencyCreate,
    ServiceDependencyOut,
    ServiceOut,
)
from app.security.auth import OrgContext, get_org_context, require_role

router = APIRouter(prefix="/organizations/{org_id}/services", tags=["services"])


def _get_service(db: Session, org_id: uuid.UUID, service_id: uuid.UUID) -> Service:
    service = (
        db.query(Service)
        .filter(Service.id == service_id, Service.organization_id == org_id)
        .first()
    )
    if service is None:
        raise NotFoundError("Service not found")
    return service


@router.post("", response_model=ServiceOut, status_code=201)
def create_service(
    payload: ServiceCreate,
    request: Request,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(require_role("responder")),
) -> Service:
    existing = (
        db.query(Service)
        .filter(Service.organization_id == ctx.org.id, Service.name == payload.name)
        .first()
    )
    if existing is not None:
        raise ConflictError("A service with that name already exists")
    service = Service(
        organization_id=ctx.org.id,
        name=payload.name,
        description=payload.description,
        tier=payload.tier,
        status=payload.status,
        owner_team=payload.owner_team,
    )
    db.add(service)
    db.flush()
    record_audit(
        db,
        organization_id=ctx.org.id,
        actor_id=ctx.user.id,
        action="service.create",
        resource_type="service",
        resource_id=service.id,
        detail={"name": payload.name},
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()
    db.refresh(service)
    return service


@router.get("", response_model=list[ServiceOut])
def list_services(
    db: Session = Depends(get_db), ctx: OrgContext = Depends(get_org_context)
) -> list[Service]:
    return (
        db.query(Service).filter(Service.organization_id == ctx.org.id).order_by(Service.name).all()
    )


@router.get("/{service_id}", response_model=ServiceOut)
def get_service(
    service_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(get_org_context),
) -> Service:
    return _get_service(db, ctx.org.id, service_id)


@router.post("/dependencies", response_model=ServiceDependencyOut, status_code=201)
def create_dependency(
    payload: ServiceDependencyCreate,
    request: Request,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(require_role("responder")),
) -> ServiceDependency:
    upstream = _get_service(db, ctx.org.id, payload.upstream_service_id)
    downstream = _get_service(db, ctx.org.id, payload.downstream_service_id)
    if upstream.id == downstream.id:
        raise ConflictError("A service cannot depend on itself")
    existing = (
        db.query(ServiceDependency)
        .filter(
            ServiceDependency.upstream_service_id == upstream.id,
            ServiceDependency.downstream_service_id == downstream.id,
            ServiceDependency.dependency_type == payload.dependency_type,
        )
        .first()
    )
    if existing is not None:
        raise ConflictError("Dependency already exists")
    dep = ServiceDependency(
        upstream_service_id=upstream.id,
        downstream_service_id=downstream.id,
        dependency_type=payload.dependency_type,
    )
    db.add(dep)
    db.flush()
    record_audit(
        db,
        organization_id=ctx.org.id,
        actor_id=ctx.user.id,
        action="service.dependency_create",
        resource_type="service_dependency",
        resource_id=str(downstream.id),
        request_id=request.headers.get("X-Request-ID"),
    )
    db.commit()
    db.refresh(dep)
    return dep


@router.get("/{service_id}/dependencies", response_model=list[ServiceDependencyOut])
def list_dependencies(
    service_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: OrgContext = Depends(get_org_context),
) -> list[ServiceDependency]:
    _get_service(db, ctx.org.id, service_id)
    return (
        db.query(ServiceDependency)
        .filter(
            (ServiceDependency.upstream_service_id == service_id)
            | (ServiceDependency.downstream_service_id == service_id)
        )
        .all()
    )
