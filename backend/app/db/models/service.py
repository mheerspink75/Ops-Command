"""Service and service-dependency models."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Service(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "services"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_service_org_name"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    tier: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    owner_team: Mapped[str | None] = mapped_column(String(200), nullable=True)


class ServiceDependency(Base):
    """Directed dependency: upstream -> downstream (downstream depends on upstream)."""

    __tablename__ = "service_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "upstream_service_id",
            "downstream_service_id",
            "dependency_type",
            name="uq_service_dependency",
        ),
    )

    upstream_service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
    )
    downstream_service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        primary_key=True,
    )
    dependency_type: Mapped[str] = mapped_column(String(32), primary_key=True, default="sync")

    upstream: Mapped[Service] = relationship(
        foreign_keys=[upstream_service_id], back_populates="upstream_of"
    )
    downstream: Mapped[Service] = relationship(
        foreign_keys=[downstream_service_id], back_populates="downstream_of"
    )


# Attach reverse relationships to Service (defined here to avoid circular imports).
Service.upstream_of = relationship(  # type: ignore[attr-defined]
    "ServiceDependency",
    foreign_keys="ServiceDependency.upstream_service_id",
    back_populates="upstream",
)
Service.downstream_of = relationship(  # type: ignore[attr-defined]
    "ServiceDependency",
    foreign_keys="ServiceDependency.downstream_service_id",
    back_populates="downstream",
)
