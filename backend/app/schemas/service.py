"""Service and dependency schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    tier: str = Field(default="standard", pattern=r"^(critical|standard|low)$")
    status: str = Field(default="active", pattern=r"^(active|degraded|down|retired)$")
    owner_team: str | None = Field(default=None, max_length=200)


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str | None
    tier: str
    status: str
    owner_team: str | None
    created_at: datetime
    updated_at: datetime


class ServiceDependencyCreate(BaseModel):
    upstream_service_id: uuid.UUID
    downstream_service_id: uuid.UUID
    dependency_type: str = Field(default="sync", pattern=r"^(sync|async|data)$")


class ServiceDependencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    upstream_service_id: uuid.UUID
    downstream_service_id: uuid.UUID
    dependency_type: str
