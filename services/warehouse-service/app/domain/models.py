"""Pydantic domain models for warehouse-service."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class PickListStatus(StrEnum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PickItemStatus(StrEnum):
    PENDING = "PENDING"
    PICKED = "PICKED"
    SHORT_PICK = "SHORT_PICK"


class PackingSlipStatus(StrEnum):
    PACKED = "PACKED"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"


class OrderType(StrEnum):
    SELL_OUT = "SELL_OUT"
    REPLENISHMENT = "REPLENISHMENT"


# ---------------------------------------------------------------------------
# BinLocation models
# ---------------------------------------------------------------------------


class BinLocation(BaseModel):
    id: uuid.UUID
    location_id: uuid.UUID
    zone: str
    aisle: str
    rack: str
    bin: str
    bin_code: str
    capacity: int | None = None
    tenant_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BinLocationCreate(BaseModel):
    location_id: uuid.UUID
    zone: str
    aisle: str
    rack: str
    bin: str
    capacity: int | None = None


# ---------------------------------------------------------------------------
# PickList models
# ---------------------------------------------------------------------------


class PickListItem(BaseModel):
    id: uuid.UUID
    pick_list_id: uuid.UUID
    product_id: uuid.UUID
    bin_location_id: uuid.UUID | None = None
    requested_quantity: int
    picked_quantity: int
    item_status: PickItemStatus

    model_config = {"from_attributes": True}


class PickList(BaseModel):
    id: uuid.UUID
    reference_order_id: str
    order_type: OrderType
    status: PickListStatus
    assigned_to: str | None = None
    tenant_id: str
    created_at: datetime
    completed_at: datetime | None = None
    items: list[PickListItem] = []

    model_config = {"from_attributes": True}


class PickListItemCreate(BaseModel):
    product_id: uuid.UUID
    bin_location_id: uuid.UUID | None = None
    requested_quantity: int = Field(gt=0)


class PickListCreate(BaseModel):
    reference_order_id: str
    order_type: OrderType
    items: list[PickListItemCreate]


class PickListAssign(BaseModel):
    assigned_to: str


class PickListItemComplete(BaseModel):
    item_id: uuid.UUID
    picked_quantity: int = Field(ge=0)


class PickListComplete(BaseModel):
    items: list[PickListItemComplete]


# ---------------------------------------------------------------------------
# PackingSlip models
# ---------------------------------------------------------------------------


class PackingSlipItem(BaseModel):
    id: uuid.UUID
    packing_slip_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    serial_numbers: list[str] = []

    model_config = {"from_attributes": True}


class PackingSlip(BaseModel):
    id: uuid.UUID
    slip_number: str
    pick_list_id: uuid.UUID
    packed_by: str
    packed_date: datetime
    shipping_carrier: str | None = None
    tracking_number: str | None = None
    status: PackingSlipStatus
    tenant_id: str
    items: list[PackingSlipItem] = []

    model_config = {"from_attributes": True}


class PackingSlipItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0)
    serial_numbers: list[str] = []


class PackingSlipCreate(BaseModel):
    pick_list_id: uuid.UUID
    packed_by: str
    items: list[PackingSlipItemCreate]


class PackingSlipDispatch(BaseModel):
    shipping_carrier: str | None = None
    tracking_number: str | None = None
