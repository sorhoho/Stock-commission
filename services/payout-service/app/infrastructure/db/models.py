from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from telco_common.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class PayoutRequest(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "payout_request"

    party_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    statement_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False, default="BANK_TRANSFER")
    bank_account_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    processed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_reference: Mapped[str | None] = mapped_column(String(200))
