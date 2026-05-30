"""Pydantic schemas for commission domain events."""

from __future__ import annotations

from pydantic import BaseModel


class CommissionEventCalculatedData(BaseModel):
    commission_event_id: str
    source_transaction_id: str
    party_id: str
    party_type: str
    agreement_id: str
    rule_id: str
    product_id: str
    quantity: int
    base_amount: float
    commission_amount: float
    commission_rate: float
    currency: str
    calculation_date: str
    tenant_id: str


class CommissionStatementConfirmedData(BaseModel):
    statement_id: str
    party_id: str
    period_year: int
    period_month: int
    total_commission: float
    currency: str
    confirmed_at: str
    tenant_id: str


class PayoutRequestCreatedData(BaseModel):
    payout_request_id: str
    party_id: str
    statement_id: str
    amount: float
    currency: str
    scheduled_date: str
    tenant_id: str


class PayoutRequestCompletedData(BaseModel):
    payout_request_id: str
    party_id: str
    amount: float
    currency: str
    external_reference: str
    processed_at: str
    tenant_id: str
