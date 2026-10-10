"""Incident and incident-related models.

Incident carries a `version` column used for optimistic concurrency control to
prevent silent lost updates when two responders modify the same incident.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow

if TYPE_CHECKING:
    from app.db.models.service import Service


class Incident(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "incidents"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="SEV3")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="declared")
    commander_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    declared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default="now()", nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    services: Mapped[list[IncidentService]] = relationship(  # noqa: F821
        back_populates="incident", cascade="all, delete-orphan"
    )
    timeline: Mapped[list[TimelineEvent]] = relationship(  # noqa: F821
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="TimelineEvent.created_at",
    )
    role_assignments: Mapped[list[IncidentRoleAssignment]] = relationship(  # noqa: F821
        back_populates="incident", cascade="all, delete-orphan"
    )
    action_items: Mapped[list[ActionItem]] = relationship(  # noqa: F821
        back_populates="incident", cascade="all, delete-orphan"
    )


class IncidentService(Base):
    """Association between an incident and an impacted service."""

    __tablename__ = "incident_services"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
    )

    incident: Mapped[Incident] = relationship(back_populates="services")
    service: Mapped[Service] = relationship()  # noqa: F821


class TimelineEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "timeline_events"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default="now()", nullable=False
    )

    incident: Mapped[Incident] = relationship(back_populates="timeline")


class IncidentRoleAssignment(Base):
    __tablename__ = "incident_role_assignments"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default="now()", nullable=False
    )

    incident: Mapped[Incident] = relationship(back_populates="role_assignments")


class ActionItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "action_items"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    incident: Mapped[Incident] = relationship(back_populates="action_items")
