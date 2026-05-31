"""Pydantic v2 domain models for sell-out-service (TMF699 Sales Management)."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum


from pydantic import BaseModel, Field


class SaleChannel(StrEnum):
    RETAIL = "RETAIL"
    ONLINE = "ONLINE"
    AGENT = "AGENT"
    KIOSK = "KIOSK"


class SaleStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    REVERSED = "REVERSED"


class SaleTransactionItemCreate(BaseModel):
    product_id: uuid.UUID
    product_name: str
    quantity: int = Field(gt=0)
    unit_price: float = Field(gt=0)
    discount_amount: float = 0.0
    serial_numbers: list[str] = []
    commission_eligible: bool = True


class SaleTransactionItem(SaleTransactionItemCreate):
    id: uuid.UUID


class SaleTransactionCreate(BaseModel):
    dealer_party_id: uuid.UUID
    customer_party_id: uuid.UUID | None = None
    channel: SaleChannel
    items: list[SaleTransactionItemCreate] = Field(min_length=1)
    sale_date: datetime | None = None


class SaleTransaction(BaseModel):
    id: uuid.UUID
    transaction_number: str
    dealer_party_id: uuid.UUID
    customer_party_id: uuid.UUID | None
    channel: SaleChannel
    items: list[SaleTransactionItem]
    total_amount: float
    currency: str = "USD"
    status: SaleStatus
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SaleTransactionUpdate(BaseModel):
    status: SaleStatus | None = None
    reversal_reason: str | None = None


class SaleTransactionSummary(BaseModel):
    dealer_party_id: uuid.UUID
    period: str
    total_transactions: int
    total_units: int
    total_amount: float
    currency: str = "USD"
