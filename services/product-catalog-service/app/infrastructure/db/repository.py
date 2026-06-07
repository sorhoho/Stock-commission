"""Repository for Product persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Product, ProductCreate, ProductType
from app.infrastructure.db import models as db_models


def _to_domain(db_p: db_models.Product) -> Product:
    return Product.model_validate(db_p)


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: ProductCreate, tenant_id: str) -> Product:
        db_p = db_models.Product(
            sku=data.sku,
            name=data.name,
            barcode=data.barcode,
            product_type=data.product_type,
            category=data.category,
            brand=data.brand,
            model_number=data.model_number,
            unit_price=data.unit_price,
            denomination=data.denomination,
            tax_rate=data.tax_rate,
            commission_eligible=data.commission_eligible,
            requires_serial_tracking=data.requires_serial_tracking,
            specifications=data.specifications,
            tenant_id=tenant_id,
        )
        self._session.add(db_p)
        await self._session.flush()
        await self._session.refresh(db_p)
        return _to_domain(db_p)

    async def get_by_id(self, product_id: uuid.UUID, tenant_id: str) -> Product | None:
        result = await self._session.execute(
            select(db_models.Product).where(
                db_models.Product.id == product_id,
                db_models.Product.tenant_id == tenant_id,
            )
        )
        db_p = result.scalar_one_or_none()
        return _to_domain(db_p) if db_p else None

    async def get_by_barcode(self, barcode: str, tenant_id: str) -> Product | None:
        result = await self._session.execute(
            select(db_models.Product).where(
                db_models.Product.barcode == barcode,
                db_models.Product.tenant_id == tenant_id,
            )
        )
        db_p = result.scalar_one_or_none()
        return _to_domain(db_p) if db_p else None

    async def list_products(
        self,
        tenant_id: str,
        product_type: ProductType | None = None,
        category: str | None = None,
        brand: str | None = None,
        search: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> list[Product]:
        query = select(db_models.Product).where(db_models.Product.tenant_id == tenant_id)
        if product_type:
            query = query.where(db_models.Product.product_type == product_type)
        if category:
            query = query.where(db_models.Product.category == category)
        if brand:
            query = query.where(db_models.Product.brand.ilike(f"%{brand}%"))
        if search:
            query = query.where(db_models.Product.name.ilike(f"%{search}%"))
        query = query.order_by(db_models.Product.product_type, db_models.Product.name)
        query = query.offset((page - 1) * size).limit(size)
        result = await self._session.execute(query)
        return [_to_domain(p) for p in result.scalars().all()]
