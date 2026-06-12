"""SQLAlchemy ORM models for commission-calculation-service."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from telco_common.db.base import Base, TimestampMixin, TenantMixin, UUIDMixin


class CommissionEvent(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "commission_event"

    source_transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    agreement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    base_amount: Mapped[float] = mapped_column(Float, nullable=False)
    commission_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="THB")
    calculation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="CALCULATED", index=True
    )


class CommissionStatement(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "commission_statement"
    __table_args__ = (
        UniqueConstraint(
            "party_id",
            "period_year",
            "period_month",
            "tenant_id",
            name="uq_commission_statement_party_period_tenant",
        ),
    )

    party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    total_commission: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="THB")
    line_items_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DRAFT", index=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ProcessedEventLog(UUIDMixin, Base):
    """
    Idempotency guard — records every (source_transaction_id, agreement_id) pair
    that has been successfully processed to prevent double-commission.
    """

    __tablename__ = "processed_event_log"
    __table_args__ = (
        UniqueConstraint(
            "source_transaction_id",
            "agreement_id",
            name="uq_processed_event_source_agreement",
        ),
    )

    source_transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    agreement_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
