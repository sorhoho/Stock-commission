"""SQLAlchemy ORM models for warehouse-service."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from telco_common.db.base import Base, TimestampMixin, TenantMixin, UUIDMixin


class BinLocation(UUIDMixin, TenantMixin, Base):
    __tablename__ = "bin_location"
    __table_args__ = (
        UniqueConstraint("location_id", "zone", "aisle", "rack", "bin", "tenant_id",
                         name="uq_bin_location"),
    )

    location_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    zone: Mapped[str] = mapped_column(String(50), nullable=False)
    aisle: Mapped[str] = mapped_column(String(50), nullable=False)
    rack: Mapped[str] = mapped_column(String(50), nullable=False)
    bin: Mapped[str] = mapped_column(String(50), nullable=False)
    bin_code: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    pick_list_items: Mapped[list["PickListItem"]] = relationship(
        "PickListItem", back_populates="bin_location", lazy="noload"
    )


class PickList(UUIDMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "pick_list"

    reference_order_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    order_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING", index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["PickListItem"]] = relationship(
        "PickListItem",
        back_populates="pick_list",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    packing_slips: Mapped[list["PackingSlip"]] = relationship(
        "PackingSlip", back_populates="pick_list", lazy="noload"
    )


class PickListItem(UUIDMixin, TenantMixin, Base):
    __tablename__ = "pick_list_item"

    pick_list_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("pick_list.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    bin_location_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("bin_location.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    picked_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    item_status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")

    pick_list: Mapped["PickList"] = relationship("PickList", back_populates="items", lazy="noload")
    bin_location: Mapped["BinLocation | None"] = relationship(
        "BinLocation", back_populates="pick_list_items", lazy="noload"
    )


class PackingSlip(UUIDMixin, TenantMixin, Base):
    __tablename__ = "packing_slip"
    __table_args__ = (
        UniqueConstraint("slip_number", "tenant_id", name="uq_packing_slip_number"),
    )

    slip_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    pick_list_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("pick_list.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    packed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    packed_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    shipping_carrier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PACKED")

    pick_list: Mapped["PickList"] = relationship(
        "PickList", back_populates="packing_slips", lazy="noload"
    )
    items: Mapped[list["PackingSlipItem"]] = relationship(
        "PackingSlipItem",
        back_populates="packing_slip",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class PackingSlipItem(UUIDMixin, TenantMixin, Base):
    __tablename__ = "packing_slip_item"

    packing_slip_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("packing_slip.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    serial_numbers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    packing_slip: Mapped["PackingSlip"] = relationship(
        "PackingSlip", back_populates="items", lazy="noload"
    )
