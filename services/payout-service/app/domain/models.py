from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PaymentMethod(StrEnum):
    BANK_TRANSFER = "BANK_TRANSFER"
    WALLET = "WALLET"
    OFFSET = "OFFSET"


class PayoutStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PayoutRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    party_id: UUID
    statement_id: UUID
    amount: float
    currency: str
    payment_method: PaymentMethod
    bank_account_ref: str
    status: PayoutStatus
    scheduled_date: date
    processed_date: datetime | None = None
    external_reference: str | None = None
    tenant_id: str
    created_at: datetime


class PayoutRequestCreate(BaseModel):
    party_id: UUID
    statement_id: UUID
    amount: float
    currency: str = "THB"
    payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    bank_account_ref: str
    scheduled_date: date
    tenant_id: str


class PayoutRequestUpdate(BaseModel):
    status: PayoutStatus | None = None
    external_reference: str | None = None
    processed_date: datetime | None = None
