"""Pydantic v2 domain models for sell-in-service (TMF622 Product Ordering)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class OrderState(StrEnum):
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# ── Order Items ───────────────────────────────────────────────────────────────

class ProductOrderItemCreate(BaseModel):
    product_id: uuid.UUID
    product_name: str
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0.0)


class ProductOrderItem(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    quantity: int
    unit_price: float


# ── Product Order ─────────────────────────────────────────────────────────────

class ProductOrderCreate(BaseModel):
    requestor_party_id: uuid.UUID
    supplier_party_id: uuid.UUID
    items: list[ProductOrderItemCreate] = Field(min_length=1)
    requested_delivery_date: date
    notes: str | None = None


class ProductOrderUpdate(BaseModel):
    state: OrderState | None = None
    actual_delivery_date: date | None = None


class ProductOrder(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    order_number: str
    requestor_party_id: uuid.UUID
    supplier_party_id: uuid.UUID
    items: list[ProductOrderItem]
    state: OrderState
    total_amount: float
    currency: str
    requested_delivery_date: date
    actual_delivery_date: date | None
    notes: str | None
    tenant_id: str
    created_at: datetime
    updated_at: datetime
