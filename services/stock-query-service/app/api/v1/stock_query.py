"""TMF637 Stock Availability query endpoints (CQRS read side)."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Query

from app.dependencies import (
    StockReadModelDep,
    TenantId)
from app.domain.models import StockAvailability, StockQueryResult
from telco_common.exceptions import NotFoundException

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/stockAvailability", tags=["StockAvailability"])


@router.get("/", response_model=StockQueryResult)
async def query_stock_availability(
    *,
    product_id: uuid.UUID | None = Query(default=None, description="Filter by product UUID"),
    location_id: uuid.UUID | None = Query(default=None, description="Filter by location UUID"),
    min_quantity: int | None = Query(default=None, ge=0, description="Minimum net quantity"),
    tenant_id: TenantId,
    read_model: StockReadModelDep,
) -> StockQueryResult:
    """Query stock availability across all locations for a tenant.

    Supports optional filtering by product, location, and minimum quantity.
    Results are served directly from the Redis read model — no DB access.
    """
    log.debug(
        "Stock availability query",
        tenant_id=tenant_id,
        product_id=str(product_id) if product_id else None,
        location_id=str(location_id) if location_id else None,
        min_quantity=min_quantity)
    raw_items = await read_model.query(
        tenant_id=tenant_id,
        product_id=str(product_id) if product_id else None,
        location_id=str(location_id) if location_id else None,
        min_quantity=min_quantity)
    items = [StockAvailability.model_validate(item) for item in raw_items]
    return StockQueryResult(items=items, total=len(items))


@router.get("/{product_id}/{location_id}", response_model=StockAvailability)
async def get_stock_availability(
    product_id: uuid.UUID,
    location_id: uuid.UUID,
    tenant_id: TenantId,
    read_model: StockReadModelDep) -> StockAvailability:
    """Get the stock availability for a specific product at a specific location.

    Returns 404 if the product/location combination has never been indexed.
    """
    entry = await read_model.get_availability(
        tenant_id=tenant_id,
        product_id=str(product_id),
        location_id=str(location_id))
    if entry is None:
        raise NotFoundException(
            "StockAvailability",
            f"{product_id}/{location_id}")
    return StockAvailability.model_validate(entry)
