"""Action item schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ActionItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    assignee_id: uuid.UUID | None = None
    status: str = Field(default="open", pattern=r"^(open|in_progress|done|cancelled)$")
    due_at: datetime | None = None


class ActionItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    assignee_id: uuid.UUID | None = None
    status: str | None = Field(default=None, pattern=r"^(open|in_progress|done|cancelled)$")
    due_at: datetime | None = None


class ActionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    title: str
    description: str | None
    assignee_id: uuid.UUID | None
    status: str
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    assignee_username: str | None = None
