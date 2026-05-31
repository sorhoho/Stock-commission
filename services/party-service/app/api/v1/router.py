"""Aggregate v1 API router for party-service."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.party import router as party_router
from app.api.v1.party_characteristic import router as party_characteristic_router

router = APIRouter(prefix="/api/v1")

router.include_router(party_router)
router.include_router(party_characteristic_router)
