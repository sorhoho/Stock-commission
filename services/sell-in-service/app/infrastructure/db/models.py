"""SQLAlchemy ORM models for sell-in-service."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from telco_common.db.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class ProductOrderDB(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "product_order"

    order_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    requestor_party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    supplier_party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ACKNOWLEDGED", index=True
    )
    total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    requested_delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list["ProductOrderItemDB"]] = relationship(
        "ProductOrderItemDB",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ProductOrderItemDB(Base, UUIDMixin):
    __tablename__ = "product_order_item"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_order.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)

    order: Mapped["ProductOrderDB"] = relationship(
        "ProductOrderDB",
        back_populates="items",
    )
