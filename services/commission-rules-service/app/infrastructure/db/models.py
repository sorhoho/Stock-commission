from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, Float, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from telco_common.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class AgreementSpec(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "agreement_spec"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    description: Mapped[str | None] = mapped_column(String(1000))
    applicable_party_roles: Mapped[list] = mapped_column(JSONB, default=list)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    is_deleted: Mapped[bool] = mapped_column(default=False)


class Agreement(Base, UUIDMixin, TenantMixin):
    __tablename__ = "agreement"
    __table_args__ = (UniqueConstraint("party_id", "agreement_spec_id", "tenant_id"),)

    agreement_spec_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    party_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    party_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    signed_date: Mapped[date] = mapped_column(Date, nullable=False)


class CommissionRule(Base, UUIDMixin, TenantMixin):
    __tablename__ = "commission_rule"

    agreement_spec_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    product_category: Mapped[str] = mapped_column(String(100), nullable=False, default="*")
    channel_type: Mapped[str | None] = mapped_column(String(50))
    tier_min_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tier_max_qty: Mapped[int | None] = mapped_column(Integer)
    commission_type: Mapped[str] = mapped_column(String(20), nullable=False)
    commission_value: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    conditions: Mapped[dict] = mapped_column(JSONB, default=dict)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_deleted: Mapped[bool] = mapped_column(default=False)
