"""API v1 router for stock-query-service."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.stock_query import router as stock_query_router

router = APIRouter(prefix="/api/v1/inventory")
router.include_router(stock_query_router)
