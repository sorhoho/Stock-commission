"""Pydantic schemas for party domain events."""

from __future__ import annotations

from pydantic import BaseModel


class PartyOnboardedData(BaseModel):
    party_id: str
    party_type: str
    name: str
    role: str
    region: str | None = None
    tier: str | None = None
    effective_date: str
    tenant_id: str
