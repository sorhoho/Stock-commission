"""Pydantic schemas for inventory domain events."""

from __future__ import annotations

from pydantic import BaseModel


class StockTransferredData(BaseModel):
    transfer_id: str
    transfer_order_number: str
    source_location_id: str
    source_location_type: str
    destination_location_id: str
    destination_location_type: str
    product_id: str
    quantity: int
    completed_at: str
    tenant_id: str


class StockAdjustedData(BaseModel):
    inventory_id: str
    product_id: str
    location_id: str
    previous_quantity: int
    new_quantity: int
    adjustment_reason: str
    adjusted_by: str
    tenant_id: str


class StockReservedData(BaseModel):
    reservation_id: str
    inventory_id: str
    reserved_quantity: int
    reserved_by: str
    reservation_expiry: str
    tenant_id: str


class StockReceivedData(BaseModel):
    grn_id: str
    grn_number: str
    supplier_reference: str | None
    product_id: str
    location_id: str
    quantity_received: int
    received_by: str
    received_date: str
    tenant_id: str


class ResourceAllocatedData(BaseModel):
    resource_id: str
    resource_type: str
    product_id: str
    characteristic_name: str
    characteristic_value: str
    allocated_to: str | None
    tenant_id: str
