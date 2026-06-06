"""Product catalog API — TMF620 product lookup endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Product, ProductCreate
from app.infrastructure.db.repository import ProductRepository
from app.infrastructure.db.session import get_db_session
from telco_common.exceptions import NotFoundException
from telco_common.middleware.tenant_middleware import get_tenant_id_from_request

router = APIRouter(prefix="/product", tags=["Product Catalog"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def _get_tenant(request) -> str:
    from fastapi import Request
    return request.state.tenant_id


from fastapi import Request


@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(body: ProductCreate, request: Request, db: DbSession) -> Product:
    """Register a product in the catalog."""
    repo = ProductRepository(db)
    return await repo.create(body, request.state.tenant_id)


@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: uuid.UUID, request: Request, db: DbSession) -> Product:
    """Get a product by ID."""
    repo = ProductRepository(db)
    product = await repo.get_by_id(product_id, request.state.tenant_id)
    if product is None:
        raise NotFoundException("Product", str(product_id))
    return product


@router.get("/", response_model=list[Product])
async def search_products(
    request: Request,
    db: DbSession,
    barcode: str | None = Query(default=None, description="Exact barcode lookup (POS scan)"),
    search: str | None = Query(default=None, description="Name search"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> list[Product]:
    """Search products by barcode (POS scan) or name substring."""
    tenant_id = request.state.tenant_id
    repo = ProductRepository(db)
    if barcode:
        product = await repo.get_by_barcode(barcode, tenant_id)
        return [product] if product else []
    if search:
        return await repo.search_by_name(search, tenant_id, page=page, size=size)
    return []
