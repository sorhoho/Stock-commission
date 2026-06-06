"""SQLAlchemy ORM models for product-catalog-service."""

from __future__ import annotations

from sqlalchemy import Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from telco_common.db.base import Base, TimestampMixin, TenantMixin, UUIDMixin


class Product(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "product"
    __table_args__ = (UniqueConstraint("barcode", "tenant_id", name="uq_product_barcode_tenant"),)

    sku: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    barcode: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    tax_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
