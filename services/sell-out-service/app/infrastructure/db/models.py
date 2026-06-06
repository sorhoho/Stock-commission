"""SQLAlchemy ORM models for sell-out-service."""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
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
    pos_session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)

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


class PosSession(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "pos_session"

    terminal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dealer_party_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    opened_by: Mapped[str] = mapped_column(String(256), nullable=False)
    opened_at: Mapped[str] = mapped_column(String(32), nullable=False)
    closed_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    opening_cash: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    closing_cash: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_transactions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class ReturnTransaction(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "return_transaction"

    return_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    original_transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sale_transaction.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    return_reason: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    returned_by: Mapped[str] = mapped_column(String(256), nullable=False)
    returned_at: Mapped[str] = mapped_column(String(32), nullable=False)

    items: Mapped[list[ReturnTransactionItem]] = relationship(
        "ReturnTransactionItem",
        back_populates="return_transaction",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ReturnTransactionItem(UUIDMixin, TenantMixin, Base):
    __tablename__ = "return_transaction_item"

    return_transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("return_transaction.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    serial_numbers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    condition: Mapped[str] = mapped_column(String(16), nullable=False, default="GOOD")

    return_transaction: Mapped[ReturnTransaction] = relationship(
        "ReturnTransaction", back_populates="items"
    )
