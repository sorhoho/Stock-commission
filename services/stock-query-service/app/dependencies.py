"""FastAPI dependency providers for stock-query-service."""

from __future__ import annotations

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status

from app.infrastructure.cache.stock_read_model import StockReadModel


def get_redis_client(request: Request) -> aioredis.Redis:
    """Return the app-level Redis client from request app state."""
    client: aioredis.Redis | None = getattr(request.app.state, "redis_client", None)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis client not available",
        )
    return client


def get_stock_read_model(request: Request) -> StockReadModel:
    """Return the app-level StockReadModel from request app state."""
    model: StockReadModel | None = getattr(request.app.state, "stock_read_model", None)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stock read model not available",
        )
    return model


def get_current_tenant_id(request: Request) -> str:
    """Extract tenant_id injected by TenantMiddleware."""
    tenant_id: str = getattr(request.state, "tenant_id", "")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Tenant-ID header",
        )
    return tenant_id


# Annotated convenience aliases
RedisClientDep = Annotated[aioredis.Redis, Depends(get_redis_client)]
StockReadModelDep = Annotated[StockReadModel, Depends(get_stock_read_model)]
TenantId = Annotated[str, Depends(get_current_tenant_id)]
