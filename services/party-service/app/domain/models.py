"""Pydantic v2 domain models for the Party service (TMF632)."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class PartyType(StrEnum):
    ORGANIZATION = "ORGANIZATION"
    INDIVIDUAL = "INDIVIDUAL"


class PartyRole(StrEnum):
    DISTRIBUTOR = "DISTRIBUTOR"
    DEALER = "DEALER"
    CHANNEL_PARTNER = "CHANNEL_PARTNER"
    SALES_EMPLOYEE = "SALES_EMPLOYEE"
    CUSTOMER = "CUSTOMER"


class PartyStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


# ---------------------------------------------------------------------------
# Party models
# ---------------------------------------------------------------------------


class Party(BaseModel):
    id: uuid.UUID
    href: str
    party_type: PartyType
    role: PartyRole
    name: str
    tax_number: str | None = None
    status: PartyStatus
    parent_party_id: uuid.UUID | None = None
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PartyCreate(BaseModel):
    party_type: PartyType
    role: PartyRole
    name: str
    tax_number: str | None = None
    status: PartyStatus = PartyStatus.ACTIVE
    parent_party_id: uuid.UUID | None = None


class PartyUpdate(BaseModel):
    name: str | None = None
    tax_number: str | None = None
    status: PartyStatus | None = None
    parent_party_id: uuid.UUID | None = None
    role: PartyRole | None = None


# ---------------------------------------------------------------------------
# PartyCharacteristic models
# ---------------------------------------------------------------------------


class PartyCharacteristic(BaseModel):
    id: uuid.UUID
    party_id: uuid.UUID
    name: str
    value: Any
    value_type: str

    model_config = {"from_attributes": True}


class PartyCharacteristicCreate(BaseModel):
    party_id: uuid.UUID
    name: str
    value: Any
    value_type: str = "string"


# ---------------------------------------------------------------------------
# PartyAccount models
# ---------------------------------------------------------------------------


class PartyAccount(BaseModel):
    id: uuid.UUID
    party_id: uuid.UUID
    account_type: str
    balance: float = 0.0
    currency: str = "USD"
    last_updated: datetime

    model_config = {"from_attributes": True}


class PartyAccountCreate(BaseModel):
    party_id: uuid.UUID
    account_type: str
    balance: float = 0.0
    currency: str = "USD"
