"""Pydantic v2 domain models for the Inventory service (TMF637)."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class LocationType(StrEnum):
    WAREHOUSE = "WAREHOUSE"
    DISTRIBUTION_CENTER = "DISTRIBUTION_CENTER"
    DEALER_OUTLET = "DEALER_OUTLET"


class InventoryStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    DAMAGED = "DAMAGED"
    IN_TRANSIT = "IN_TRANSIT"


class TransferStatus(StrEnum):
    PENDING = "PENDING"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# Location models
# ---------------------------------------------------------------------------


class Location(BaseModel):
    id: uuid.UUID
    name: str
    type: LocationType
    address: str | None = None
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LocationCreate(BaseModel):
    name: str
    type: LocationType
    address: str | None = None


class LocationUpdate(BaseModel):
    name: str | None = None
    type: LocationType | None = None
    address: str | None = None


# ---------------------------------------------------------------------------
# ProductInventory models
# ---------------------------------------------------------------------------


class ProductInventory(BaseModel):
    id: uuid.UUID
    href: str
    product_id: uuid.UUID
    product_name: str
    quantity: int
    quantity_uom: str = "EACH"
    location_id: uuid.UUID
    location_type: LocationType
    serial_number_range_start: str | None = None
    serial_number_range_end: str | None = None
    status: InventoryStatus
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductInventoryCreate(BaseModel):
    product_id: uuid.UUID
    product_name: str
    quantity: int = Field(ge=0)
    quantity_uom: str = "EACH"
    location_id: uuid.UUID
    location_type: LocationType
    serial_number_range_start: str | None = None
    serial_number_range_end: str | None = None
    status: InventoryStatus = InventoryStatus.AVAILABLE


class ProductInventoryUpdate(BaseModel):
    product_name: str | None = None
    quantity: int | None = Field(default=None, ge=0)
    quantity_uom: str | None = None
    location_id: uuid.UUID | None = None
    location_type: LocationType | None = None
    serial_number_range_start: str | None = None
    serial_number_range_end: str | None = None
    status: InventoryStatus | None = None


# ---------------------------------------------------------------------------
# StockTransfer models
# ---------------------------------------------------------------------------


class StockTransfer(BaseModel):
    id: uuid.UUID
    transfer_order_number: str
    source_location_id: uuid.UUID
    destination_location_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    status: TransferStatus
    initiated_by: str
    tenant_id: str
    requested_date: datetime
    completed_date: datetime | None = None

    model_config = {"from_attributes": True}


class StockTransferCreate(BaseModel):
    transfer_order_number: str
    source_location_id: uuid.UUID
    destination_location_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int = Field(gt=0)
    initiated_by: str
    requested_date: datetime


class StockTransferUpdate(BaseModel):
    status: TransferStatus | None = None
    completed_date: datetime | None = None
