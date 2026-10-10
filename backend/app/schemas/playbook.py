"""Playbook and playbook-run schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlaybookStep(BaseModel):
    type: str = Field(
        pattern=r"^(timeline_message|create_action_item|change_status|wait|mock_webhook|snapshot)$"
    )
    params: dict = Field(default_factory=dict)


class PlaybookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    enabled: bool = True
    steps: list[PlaybookStep] = Field(default_factory=list)


class PlaybookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str | None
    enabled: bool
    steps: list
    created_at: datetime
    updated_at: datetime


class PlaybookRunStart(BaseModel):
    playbook_id: uuid.UUID
    # Optional idempotency key; generated server-side if omitted.
    idempotency_key: str | None = Field(default=None, max_length=200)


class PlaybookRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    playbook_id: uuid.UUID
    status: str
    idempotency_key: str
    started_at: datetime | None
    completed_at: datetime | None
    error_detail: str | None
    progress: list
    created_at: datetime
