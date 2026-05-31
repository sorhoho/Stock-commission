from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CommissionType(StrEnum):
    FLAT_AMOUNT = "FLAT_AMOUNT"
    PERCENTAGE = "PERCENTAGE"
    TIERED = "TIERED"


class AgreementStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"


class AgreementSpec(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    version: str
    description: str | None = None
    applicable_party_roles: list[str]
    effective_from: date
    effective_to: date | None = None
    tenant_id: str
    created_at: datetime
    updated_at: datetime


class AgreementSpecCreate(BaseModel):
    name: str
    version: str = "1.0"
    description: str | None = None
    applicable_party_roles: list[str] = ["DEALER"]
    effective_from: date
    effective_to: date | None = None
    tenant_id: str


class AgreementSpecUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    effective_to: date | None = None
    applicable_party_roles: list[str] | None = None


class Agreement(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    agreement_spec_id: UUID
    party_id: UUID
    party_name: str
    status: AgreementStatus
    signed_date: date
    tenant_id: str


class AgreementCreate(BaseModel):
    agreement_spec_id: UUID
    party_id: UUID
    party_name: str
    signed_date: date
    tenant_id: str


class AgreementUpdate(BaseModel):
    status: AgreementStatus | None = None


class CommissionRule(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    agreement_spec_id: UUID
    product_category: str
    channel_type: str | None = None
    tier_min_qty: int = 0
    tier_max_qty: int | None = None
    commission_type: CommissionType
    commission_value: float
    currency: str = "USD"
    conditions: dict[str, Any] = {}
    priority: int = 100
    tenant_id: str


class CommissionRuleCreate(BaseModel):
    agreement_spec_id: UUID
    product_category: str = "*"
    channel_type: str | None = None
    tier_min_qty: int = 0
    tier_max_qty: int | None = None
    commission_type: CommissionType
    commission_value: float
    currency: str = "USD"
    conditions: dict[str, Any] = {}
    priority: int = 100
    tenant_id: str


class CommissionRuleUpdate(BaseModel):
    product_category: str | None = None
    channel_type: str | None = None
    tier_min_qty: int | None = None
    tier_max_qty: int | None = None
    commission_type: CommissionType | None = None
    commission_value: float | None = None
    priority: int | None = None


class AgreementWithRules(BaseModel):
    """Response model for commission-calculation-service — agreement + all active rules."""
    model_config = ConfigDict(from_attributes=True)
    id: str
    agreement_spec_id: str
    party_id: str
    party_name: str
    status: str
    rules: list[CommissionRule]
