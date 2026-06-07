"""SQLAlchemy ORM models for product-catalog-service."""

from __future__ import annotations

from sqlalchemy import Boolean, Float, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from telco_common.db.base import Base, TimestampMixin, TenantMixin, UUIDMixin


class Product(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "product"
    __table_args__ = (UniqueConstraint("barcode", "tenant_id", name="uq_product_barcode_tenant"),)

    sku: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    barcode: Mapped[str] = mapped_column(String(64), nullable=False)
    product_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    model_number: Mapped[str | None] = mapped_column(String(256), nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    denomination: Mapped[float | None] = mapped_column(Float, nullable=True)
    tax_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    commission_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_serial_tracking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    specifications: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
