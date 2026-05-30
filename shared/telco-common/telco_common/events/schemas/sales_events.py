"""Pydantic schemas for sales domain events."""

from __future__ import annotations

from pydantic import BaseModel


class SaleTransactionItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    serial_numbers: list[str] = []
    commission_eligible: bool = True


class SellOutCompletedData(BaseModel):
    transaction_id: str
    transaction_number: str
    dealer_party_id: str
    dealer_name: str
    channel: str
    sale_date: str
    total_amount: float
    currency: str
    items: list[SaleTransactionItem]
    tenant_id: str


class SellInOrderedData(BaseModel):
    order_id: str
    order_number: str
    requestor_party_id: str
    supplier_party_id: str
    items: list[dict]
    requested_delivery_date: str
    tenant_id: str


class SellInDeliveredData(BaseModel):
    order_id: str
    order_number: str
    delivered_at: str
    delivered_items: list[dict]
    destination_location_id: str
    tenant_id: str
