"""API v1 router for product-catalog-service."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.product import router as product_router

router = APIRouter(prefix="/api/v1/productCatalog")

router.include_router(product_router)
