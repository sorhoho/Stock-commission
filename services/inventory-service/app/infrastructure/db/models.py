"""SQLAlchemy ORM models for the Inventory service."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
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


class GoodsReceipt(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "goods_receipt"
    __table_args__ = (
        UniqueConstraint("grn_number", "tenant_id", name="uq_goods_receipt_grn_tenant"),
    )

    grn_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    supplier_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("location.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    received_by: Mapped[str] = mapped_column(String(255), nullable=False)
    received_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Resource(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """TMF 639 Resource — individual physical device, SIM card, or accessory."""

    __tablename__ = "resource"

    resource_name: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    inventory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_inventory.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("location.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="AVAILABLE", index=True
    )
    batch_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    supplier_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    allocated_to: Mapped[str | None] = mapped_column(String(255), nullable=True)

    characteristics: Mapped[list["ResourceCharacteristic"]] = relationship(
        "ResourceCharacteristic",
        back_populates="resource",
        lazy="noload",
        cascade="all, delete-orphan",
    )


class ResourceCharacteristic(Base, UUIDMixin, TenantMixin):
    """TMF 639 ResourceCharacteristic — IMEI, ICCID, serial number, etc."""

    __tablename__ = "resource_characteristic"
    # One characteristic name per resource; identity values (IMEI, ICCID …) are
    # globally unique per tenant via a partial index in the migration.
    __table_args__ = (
        UniqueConstraint("resource_id", "name", name="uq_resource_characteristic_resource_name"),
    )

    resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resource.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    resource: Mapped["Resource"] = relationship(
        "Resource", back_populates="characteristics", lazy="noload"
    )


class StockReconciliation(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "stock_reconciliation"

    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("location.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reconciliation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="DRAFT", index=True
    )
    counted_by: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list["StockReconciliationItem"]] = relationship(
        "StockReconciliationItem",
        back_populates="reconciliation",
        lazy="noload",
        cascade="all, delete-orphan",
    )


class StockReconciliationItem(Base, UUIDMixin, TenantMixin):
    __tablename__ = "stock_reconciliation_item"

    reconciliation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_reconciliation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    system_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    physical_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    variance: Mapped[int] = mapped_column(Integer, nullable=False)

    reconciliation: Mapped["StockReconciliation"] = relationship(
        "StockReconciliation", back_populates="items", lazy="noload"
    )
