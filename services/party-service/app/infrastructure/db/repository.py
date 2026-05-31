"""Async repository classes for the Party service."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import PartyCreate, PartyRole, PartyStatus, PartyUpdate
from app.infrastructure.db import models as orm


class PartyRepository:
    """Data-access layer for Party entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: PartyCreate, tenant_id: str) -> orm.Party:
        party = orm.Party(
            party_type=data.party_type,
            role=data.role,
            name=data.name,
            tax_number=data.tax_number,
            status=data.status,
            parent_party_id=data.parent_party_id,
            tenant_id=tenant_id,
        )
        self._session.add(party)
        await self._session.flush()
        await self._session.refresh(party)
        return party

    async def get_by_id(
        self, party_id: uuid.UUID, tenant_id: str
    ) -> orm.Party | None:
        result = await self._session.execute(
            select(orm.Party).where(
                orm.Party.id == party_id,
                orm.Party.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_with_filters(
        self,
        tenant_id: str,
        role: PartyRole | None = None,
        status: PartyStatus | None = None,
        parent_party_id: uuid.UUID | None = None,
        page: int = 1,
        size: int = 20,
    ) -> Sequence[orm.Party]:
        query = select(orm.Party).where(orm.Party.tenant_id == tenant_id)
        if role is not None:
            query = query.where(orm.Party.role == role)
        if status is not None:
            query = query.where(orm.Party.status == status)
        if parent_party_id is not None:
            query = query.where(orm.Party.parent_party_id == parent_party_id)
        offset = (page - 1) * size
        query = query.order_by(orm.Party.name).offset(offset).limit(size)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def update(
        self, party_id: uuid.UUID, tenant_id: str, data: PartyUpdate
    ) -> orm.Party | None:
        party = await self.get_by_id(party_id, tenant_id)
        if party is None:
            return None
        patch = data.model_dump(exclude_none=True)
        for field, value in patch.items():
            setattr(party, field, value)
        await self._session.flush()
        await self._session.refresh(party)
        return party

    async def soft_delete(
        self, party_id: uuid.UUID, tenant_id: str
    ) -> orm.Party | None:
        """Soft-delete by setting status to TERMINATED."""
        party = await self.get_by_id(party_id, tenant_id)
        if party is None:
            return None
        party.status = PartyStatus.TERMINATED
        await self._session.flush()
        await self._session.refresh(party)
        return party

    async def get_ancestors(
        self, party_id: uuid.UUID, tenant_id: str
    ) -> list[orm.Party]:
        """Walk parent_party_id chain from root to the given party.

        Returns the chain in root-first order (including the party itself).
        Protects against cycles by limiting depth.
        """
        chain: list[orm.Party] = []
        current_id: uuid.UUID | None = party_id
        seen: set[uuid.UUID] = set()
        max_depth = 20

        while current_id is not None and len(chain) < max_depth:
            if current_id in seen:
                break  # Cycle guard
            seen.add(current_id)

            result = await self._session.execute(
                select(orm.Party).where(
                    orm.Party.id == current_id,
                    orm.Party.tenant_id == tenant_id,
                )
            )
            party = result.scalar_one_or_none()
            if party is None:
                break
            chain.append(party)
            current_id = party.parent_party_id

        # Reverse so root comes first
        chain.reverse()
        return chain
