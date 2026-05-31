"""SQLAlchemy ORM models for the Inventory service."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from telco_common.db.base import Base, TimestampMixin, TenantMixin, UUIDMixin


class Location(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "location"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    inventory_items: Mapped[list["ProductInventory"]] = relationship(
        "ProductInventory",
        foreign_keys="ProductInventory.location_id",
        back_populates="location",
        lazy="noload",
    )
    outbound_transfers: Mapped[list["StockTransfer"]] = relationship(
        "StockTransfer",
        foreign_keys="StockTransfer.source_location_id",
        back_populates="source_location",
        lazy="noload",
    )
    inbound_transfers: Mapped[list["StockTransfer"]] = relationship(
        "StockTransfer",
        foreign_keys="StockTransfer.destination_location_id",
        back_populates="destination_location",
        lazy="noload",
    )


class ProductInventory(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "product_inventory"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity_uom: Mapped[str] = mapped_column(String(20), nullable=False, default="EACH")
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("location.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    location_type: Mapped[str] = mapped_column(String(50), nullable=False)
    serial_number_range_start: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    serial_number_range_end: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="AVAILABLE", index=True
    )

    # Relationships
    location: Mapped["Location"] = relationship(
        "Location",
        foreign_keys=[location_id],
        back_populates="inventory_items",
        lazy="noload",
    )
    reservations: Mapped[list["StockReservation"]] = relationship(
        "StockReservation",
        back_populates="inventory",
        lazy="noload",
    )

    @property
    def href(self) -> str:
        return f"/api/v1/productInventory/{self.id}"


class StockTransfer(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "stock_transfer"
    __table_args__ = (
        UniqueConstraint("transfer_order_number", name="uq_stock_transfer_order_number"),
    )

    transfer_order_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    source_location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("location.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    destination_location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("location.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING", index=True
    )
    initiated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    source_location: Mapped["Location"] = relationship(
        "Location",
        foreign_keys=[source_location_id],
        back_populates="outbound_transfers",
        lazy="noload",
    )
    destination_location: Mapped["Location"] = relationship(
        "Location",
        foreign_keys=[destination_location_id],
        back_populates="inbound_transfers",
        lazy="noload",
    )


class StockReservation(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "stock_reservation"

    inventory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_inventory.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reserved_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_by: Mapped[str] = mapped_column(String(255), nullable=False)
    reservation_expiry: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    inventory: Mapped["ProductInventory"] = relationship(
        "ProductInventory",
        back_populates="reservations",
        lazy="noload",
    )
