from fastapi import APIRouter
from app.api.v1.payout_request import router as payout_router

router = APIRouter(prefix="/api/v1/payout")
router.include_router(payout_router)
