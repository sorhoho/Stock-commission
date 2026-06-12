"""Pydantic v2 domain models for sell-out-service (TMF699 Sales Management)."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum


from pydantic import BaseModel, Field


class PaymentMethod(StrEnum):
    CASH = "CASH"
    CARD = "CARD"
    MOBILE_MONEY = "MOBILE_MONEY"
    CREDIT = "CREDIT"


class PosSessionStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ReturnStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ReturnCondition(StrEnum):
    GOOD = "GOOD"
    DAMAGED = "DAMAGED"
    FAULTY = "FAULTY"


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
    pos_session_id: uuid.UUID | None = None
    payment_method: PaymentMethod | None = None
    payment_reference: str | None = None


class SaleTransaction(BaseModel):
    id: uuid.UUID
    transaction_number: str
    dealer_party_id: uuid.UUID
    customer_party_id: uuid.UUID | None
    channel: SaleChannel
    items: list[SaleTransactionItem]
    total_amount: float
    currency: str = "THB"
    status: SaleStatus
    pos_session_id: uuid.UUID | None = None
    payment_method: str | None = None
    payment_reference: str | None = None
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
    currency: str = "THB"


# ---------------------------------------------------------------------------
# POS Session models
# ---------------------------------------------------------------------------

class PosSessionCreate(BaseModel):
    terminal_id: str
    dealer_party_id: uuid.UUID
    opened_by: str
    opening_cash: float = 0.0


class PosSessionClose(BaseModel):
    closing_cash: float = 0.0


class PosSession(BaseModel):
    id: uuid.UUID
    terminal_id: str
    dealer_party_id: uuid.UUID
    opened_by: str
    opened_at: str
    closed_at: str | None = None
    status: PosSessionStatus
    opening_cash: float
    closing_cash: float | None = None
    total_transactions: int
    total_amount: float
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Return Transaction models
# ---------------------------------------------------------------------------

class ReturnTransactionItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0)
    serial_numbers: list[str] = []
    condition: ReturnCondition = ReturnCondition.GOOD


class ReturnTransactionItem(BaseModel):
    id: uuid.UUID
    return_transaction_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    serial_numbers: list[str] = []
    condition: ReturnCondition
    tenant_id: str

    model_config = {"from_attributes": True}


class ReturnTransactionCreate(BaseModel):
    original_transaction_id: uuid.UUID | None = None
    return_reason: str
    returned_by: str
    items: list[ReturnTransactionItemCreate] = Field(min_length=1)


class ReturnTransaction(BaseModel):
    id: uuid.UUID
    return_number: str
    original_transaction_id: uuid.UUID | None
    return_reason: str
    status: ReturnStatus
    returned_by: str
    returned_at: str
    items: list[ReturnTransactionItem] = []
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
