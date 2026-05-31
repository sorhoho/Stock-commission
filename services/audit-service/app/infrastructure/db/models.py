"""Append-only audit log — never updated, only inserted."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from telco_common.db.base import Base, UUIDMixin


class AuditLog(Base, UUIDMixin):
    """Partitioned by received_at month for long-term retention (7 years)."""
    __tablename__ = "audit_log"
    __table_args__ = (UniqueConstraint("event_id", name="uq_audit_log_event_id"),)

    event_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_source: Mapped[str] = mapped_column(String(200), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    event_time: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
