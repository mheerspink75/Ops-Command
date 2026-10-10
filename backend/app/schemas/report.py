"""Post-incident report schema."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ReportOut(BaseModel):
    incident_id: uuid.UUID
    format: str = "markdown"
    generated_at: datetime
    content: str
