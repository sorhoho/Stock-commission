"""Product catalog API — TMF620 product lookup endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Product, ProductCreate, ProductType
from app.infrastructure.db.repository import ProductRepository
from app.infrastructure.db.session import get_db_session
from telco_common.exceptions import NotFoundException

router = APIRouter(prefix="/product", tags=["Product Catalog"])

DbSession = Depends(get_db_session)


@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(body: ProductCreate, request: Request, db: AsyncSession = DbSession) -> Product:
    """Register a new product in the catalog."""
    return await ProductRepository(db).create(body, request.state.tenant_id)


@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: uuid.UUID, request: Request, db: AsyncSession = DbSession) -> Product:
    """Get a product by ID."""
    product = await ProductRepository(db).get_by_id(product_id, request.state.tenant_id)
    if product is None:
        raise NotFoundException("Product", str(product_id))
    return product


@router.get("/", response_model=list[Product])
async def list_products(
    request: Request,
    db: AsyncSession = DbSession,
    barcode: str | None = Query(default=None, description="Exact barcode — for POS scan"),
    product_type: ProductType | None = Query(default=None, description="Filter by product type"),
    category: str | None = Query(default=None, description="Filter by commercial category"),
    brand: str | None = Query(default=None, description="Filter by brand (partial match)"),
    search: str | None = Query(default=None, description="Name substring search"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> list[Product]:
    """
    List / search products.

    - `barcode` — exact POS scan lookup; returns at most one result.
    - `product_type` — filter by HANDSET, SIM_CARD, SET_TOP_BOX, etc.
    - `category` — filter by commercial category (PREPAID, TV, DATA, etc.).
    - `brand` / `search` — partial-match filters.
    """
    repo = ProductRepository(db)
    tenant_id = request.state.tenant_id
    if barcode:
        product = await repo.get_by_barcode(barcode, tenant_id)
        return [product] if product else []
    return await repo.list_products(
        tenant_id,
        product_type=product_type,
        category=category,
        brand=brand,
        search=search,
        page=page,
        size=size,
    )
