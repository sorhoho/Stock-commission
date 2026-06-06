"""Pydantic schemas for warehouse domain events."""

from __future__ import annotations

from pydantic import BaseModel


class PickListCreatedData(BaseModel):
    pick_list_id: str
    reference_order_id: str
    order_type: str
    item_count: int
    tenant_id: str


class PickListCompletedData(BaseModel):
    pick_list_id: str
    reference_order_id: str
    order_type: str
    assigned_to: str | None
    completed_at: str
    tenant_id: str


class DispatchCreatedData(BaseModel):
    slip_id: str
    slip_number: str
    pick_list_id: str
    shipping_carrier: str | None
    tracking_number: str | None
    packed_by: str
    tenant_id: str
