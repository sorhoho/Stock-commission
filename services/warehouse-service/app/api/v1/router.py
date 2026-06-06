"""Aggregate v1 router for warehouse-service."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.bin_location import router as bin_router
from app.api.v1.packing_slip import router as packing_router
from app.api.v1.pick_list import router as pick_router

router = APIRouter(prefix="/api/v1/warehouseManagement")

router.include_router(bin_router)
router.include_router(pick_router)
router.include_router(packing_router)
