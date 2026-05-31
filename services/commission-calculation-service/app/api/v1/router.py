from fastapi import APIRouter

from app.api.v1.commission_event import router as commission_event_router
from app.api.v1.commission_statement import router as commission_statement_router

router = APIRouter(prefix="/api/v1/accountManagement")
router.include_router(commission_event_router)
router.include_router(commission_statement_router)
