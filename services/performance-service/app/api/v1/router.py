"""API v1 router for performance-service."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.indicator_spec import router as indicator_spec_router
from app.api.v1.target import router as target_router
from app.api.v1.measurement import router as measurement_router
from app.api.v1.dashboard import router as dashboard_router

router = APIRouter(prefix="/api/v1/performanceManagement")

router.include_router(indicator_spec_router)
router.include_router(target_router)
router.include_router(measurement_router)
router.include_router(dashboard_router)
