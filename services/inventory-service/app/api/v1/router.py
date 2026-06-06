"""Aggregate v1 API router for inventory-service."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.goods_receipt import router as goods_receipt_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.location import router as location_router
from app.api.v1.reconciliation import router as reconciliation_router
from app.api.v1.resource_inventory import router as resource_router
from app.api.v1.stock_adjustment import router as stock_adjustment_router
from app.api.v1.stock_reservation import router as stock_reservation_router
from app.api.v1.transfer import router as transfer_router

router = APIRouter(prefix="/api/v1")

# TMF 637 — Product Inventory
router.include_router(inventory_router)
router.include_router(transfer_router)
router.include_router(location_router)

# Inventory operations
router.include_router(goods_receipt_router)
router.include_router(stock_reservation_router)
router.include_router(stock_adjustment_router)
router.include_router(reconciliation_router)

# TMF 639 — Resource Inventory (individual device/SIM/serial tracking)
resource_api = APIRouter(prefix="/resourceInventory")
resource_api.include_router(resource_router)
router.include_router(resource_api)
