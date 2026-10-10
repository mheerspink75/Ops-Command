"""Organization and membership schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, min_length=2, max_length=200, pattern=r"^[a-z0-9-]+$")


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime


class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: str
    created_at: datetime
    # Populated by the API layer (not a DB column).
    username: str | None = None
    email: EmailStr | None = None


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="responder", pattern=r"^(owner|administrator|responder|viewer)$")
