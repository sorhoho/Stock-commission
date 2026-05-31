from fastapi import APIRouter

from app.api.v1.agreement_spec import router as agreement_spec_router
from app.api.v1.agreement import router as agreement_router
from app.api.v1.commission_rule import router as commission_rule_router

router = APIRouter(prefix="/api/v1/agreementManagement")
router.include_router(agreement_spec_router)
router.include_router(agreement_router)
router.include_router(commission_rule_router)
