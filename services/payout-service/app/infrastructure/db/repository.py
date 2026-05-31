from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import PayoutRequest


class PayoutRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, request: PayoutRequest) -> PayoutRequest:
        self._session.add(request)
        await self._session.flush()
        return request

    async def get_by_id(self, request_id: str) -> PayoutRequest | None:
        result = await self._session.execute(select(PayoutRequest).where(PayoutRequest.id == request_id))
        return result.scalar_one_or_none()

    async def list_with_filters(self, tenant_id: str, party_id: str | None = None, status: str | None = None) -> list[PayoutRequest]:
        q = select(PayoutRequest).where(PayoutRequest.tenant_id == tenant_id)
        if party_id:
            q = q.where(PayoutRequest.party_id == party_id)
        if status:
            q = q.where(PayoutRequest.status == status)
        result = await self._session.execute(q.order_by(PayoutRequest.created_at.desc()))
        return list(result.scalars())

    async def update_status(self, request_id: str, status: str, external_reference: str | None = None) -> None:
        values: dict = {"status": status}
        if external_reference:
            values["external_reference"] = external_reference
        await self._session.execute(update(PayoutRequest).where(PayoutRequest.id == request_id).values(**values))
