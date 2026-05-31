"""SQLAlchemy ORM models for the Performance service."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from telco_common.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class PerformanceIndicatorSpecDB(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "performance_indicator_spec"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_of_measure: Mapped[str] = mapped_column(String(64), nullable=False)
    indicator_type: Mapped[str] = mapped_column(String(32), nullable=False)
    measurement_interval: Mapped[str] = mapped_column(String(32), nullable=False)

    targets: Mapped[list[PerformanceTargetDB]] = relationship(
        "PerformanceTargetDB", back_populates="spec", lazy="select"
    )
    measurements: Mapped[list[PerformanceMeasurementDB]] = relationship(
        "PerformanceMeasurementDB", back_populates="spec", lazy="select"
    )


class PerformanceTargetDB(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "performance_target"

    party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    kpi_spec_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("performance_indicator_spec.id"),
        nullable=False,
        index=True,
    )
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

    spec: Mapped[PerformanceIndicatorSpecDB] = relationship(
        "PerformanceIndicatorSpecDB", back_populates="targets"
    )


class PerformanceMeasurementDB(Base, UUIDMixin, TenantMixin):
    __tablename__ = "performance_measurement"

    party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    kpi_spec_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("performance_indicator_spec.id"),
        nullable=False,
        index=True,
    )
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    measured_value: Mapped[float] = mapped_column(Float, nullable=False)
    source_event_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    spec: Mapped[PerformanceIndicatorSpecDB] = relationship(
        "PerformanceIndicatorSpecDB", back_populates="measurements"
    )
