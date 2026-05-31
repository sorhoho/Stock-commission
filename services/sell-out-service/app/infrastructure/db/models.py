"""SQLAlchemy ORM models for sell-out-service."""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from telco_common.db.base import Base, TimestampMixin, TenantMixin, UUIDMixin


class SaleTransaction(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "sale_transaction"

    transaction_number: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    dealer_party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    customer_party_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    items: Mapped[list[SaleTransactionItem]] = relationship(
        "SaleTransactionItem",
        back_populates="transaction",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SaleTransactionItem(UUIDMixin, Base):
    __tablename__ = "sale_transaction_item"

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sale_transaction.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_name: Mapped[str] = mapped_column(String(256), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    discount_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    serial_numbers: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    commission_eligible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    transaction: Mapped[SaleTransaction] = relationship(
        "SaleTransaction", back_populates="items"
    )
