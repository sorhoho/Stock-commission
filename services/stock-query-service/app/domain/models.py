"""Pydantic v2 domain models for the stock-query read-model service."""

from __future__ import annotations

import uuid
from typing import Annotated

from pydantic import BaseModel, Field, computed_field


class StockAvailability(BaseModel):
    """Read-model projection of stock availability at a given location."""

    product_id: uuid.UUID
    product_name: str
    location_id: uuid.UUID
    location_type: str
    available_quantity: int = Field(ge=0)
    reserved_quantity: int = Field(default=0, ge=0)
    last_updated: str
    tenant_id: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def net_quantity(self) -> int:
        """Net quantity = available minus reserved (floor 0)."""
        return max(0, self.available_quantity - self.reserved_quantity)

    model_config = {"from_attributes": True}


class StockQueryResult(BaseModel):
    """Paginated container for availability query results."""

    items: list[StockAvailability]
    total: int = Field(ge=0)
