from fastapi import APIRouter
from app.api.v1.audit_log import router as audit_router

router = APIRouter(prefix="/api/v1/audit")
router.include_router(audit_router)
