"""Aggregate v1 API router for inventory-service."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.inventory import router as inventory_router
from app.api.v1.location import router as location_router
from app.api.v1.transfer import router as transfer_router

router = APIRouter(prefix="/api/v1")

router.include_router(inventory_router)
router.include_router(transfer_router)
router.include_router(location_router)
