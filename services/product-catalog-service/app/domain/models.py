"""Pydantic domain models for product-catalog-service (TMF620)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    sku: str
    name: str
    barcode: str
    category: str
    unit_price: float = Field(ge=0)
    tax_rate: float = Field(ge=0, le=1, default=0.0)


class Product(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    barcode: str
    category: str
    unit_price: float
    tax_rate: float
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
