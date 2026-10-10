"""Timeline event schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TimelineEventCreate(BaseModel):
    event_type: str = Field(default="update", max_length=64)
    message: str = Field(min_length=1, max_length=5000)
    metadata: dict | None = None


class TimelineEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    event_type: str
    message: str
    metadata: dict | None
    actor_id: uuid.UUID | None
    created_at: datetime
    actor_username: str | None = None
