"""Top-level API v1 router for sell-out-service."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.pos_session import router as pos_session_router
from app.api.v1.return_transaction import router as return_transaction_router
from app.api.v1.sale_transaction import router as sale_transaction_router

router = APIRouter(prefix="/api/v1/salesManagement")

router.include_router(sale_transaction_router)
router.include_router(pos_session_router)
router.include_router(return_transaction_router)
