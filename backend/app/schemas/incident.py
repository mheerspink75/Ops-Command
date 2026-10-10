"""Incident and related schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.service import ServiceOut


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    summary: str | None = Field(default=None, max_length=5000)
    severity: str = Field(default="SEV3", pattern=r"^(SEV1|SEV2|SEV3|SEV4)$")
    service_ids: list[uuid.UUID] = Field(default_factory=list)
    commander_id: uuid.UUID | None = None


class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=300)
    summary: str | None = Field(default=None, max_length=5000)
    severity: str | None = Field(default=None, pattern=r"^(SEV1|SEV2|SEV3|SEV4)$")
    service_ids: list[uuid.UUID] | None = None
    commander_id: uuid.UUID | None = None
    # Optimistic concurrency: the version the client last observed.
    expected_version: int | None = None


class IncidentStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(declared|investigating|identified|monitoring|resolved|closed)$")
    expected_version: int | None = None


class IncidentRoleAssign(BaseModel):
    user_id: uuid.UUID
    role: str = Field(pattern=r"^(commander|communications|operations|scribe)$")


class IncidentRoleAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    role: str
    assigned_at: datetime
    username: str | None = None


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    title: str
    summary: str | None
    severity: str
    status: str
    commander_id: uuid.UUID | None
    created_by_id: uuid.UUID
    declared_at: datetime
    resolved_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime
    services: list[ServiceOut] = Field(default_factory=list)
    role_assignments: list[IncidentRoleAssignmentOut] = Field(default_factory=list)
