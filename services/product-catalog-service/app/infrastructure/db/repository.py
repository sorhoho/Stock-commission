"""Repository for Product persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Product, ProductCreate
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
            category=data.category,
            unit_price=data.unit_price,
            tax_rate=data.tax_rate,
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

    async def search_by_name(
        self, name: str, tenant_id: str, page: int = 1, size: int = 20
    ) -> list[Product]:
        query = (
            select(db_models.Product)
            .where(
                db_models.Product.tenant_id == tenant_id,
                db_models.Product.name.ilike(f"%{name}%"),
            )
            .order_by(db_models.Product.name)
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self._session.execute(query)
        return [_to_domain(p) for p in result.scalars().all()]
