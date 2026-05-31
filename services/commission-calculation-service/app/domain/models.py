"""Pydantic v2 domain models for commission-calculation-service (TMF666)."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class CommissionEventStatus(StrEnum):
    CALCULATED = "CALCULATED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    DISPUTED = "DISPUTED"


class CommissionStatementStatus(StrEnum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    PAID = "PAID"


class CommissionEvent(BaseModel):
    id: uuid.UUID
    source_transaction_id: uuid.UUID
    party_id: uuid.UUID
    agreement_id: uuid.UUID
    rule_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    base_amount: float
    commission_amount: float
    currency: str
    calculation_date: datetime
    status: CommissionEventStatus
    tenant_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CommissionStatement(BaseModel):
    id: uuid.UUID
    party_id: uuid.UUID
    period_year: int
    period_month: int
    total_commission: float
    currency: str = "USD"
    line_items_count: int
    status: CommissionStatementStatus
    confirmed_at: datetime | None
    tenant_id: str

    model_config = {"from_attributes": True}


class CommissionStatementConfirmRequest(BaseModel):
    """Request body for confirming a commission statement."""
    pass  # confirmation requires no additional body fields


class CommissionDisputeRequest(BaseModel):
    """Request body for disputing a commission event."""
    reason: str = Field(..., min_length=1, max_length=1000)


class CommissionRecalculateRequest(BaseModel):
    """Admin request to trigger recalculation for a party/period."""
    party_id: uuid.UUID
    year: int = Field(..., ge=2020, le=2100)
    month: int = Field(..., ge=1, le=12)
