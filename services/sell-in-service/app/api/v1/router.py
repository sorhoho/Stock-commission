from fastapi import APIRouter
from app.api.v1.product_order import router as product_order_router

router = APIRouter(prefix="/api/v1/productOrdering")
router.include_router(product_order_router)
