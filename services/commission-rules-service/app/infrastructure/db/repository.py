from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Agreement, AgreementSpec, CommissionRule


class AgreementSpecRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, spec: AgreementSpec) -> AgreementSpec:
        self._session.add(spec)
        await self._session.flush()
        return spec

    async def get_by_id(self, spec_id: str) -> AgreementSpec | None:
        result = await self._session.execute(select(AgreementSpec).where(AgreementSpec.id == uuid.UUID(spec_id), ~AgreementSpec.is_deleted))
        return result.scalar_one_or_none()

    async def list_active(self, tenant_id: str) -> list[AgreementSpec]:
        result = await self._session.execute(
            select(AgreementSpec).where(AgreementSpec.tenant_id == tenant_id, ~AgreementSpec.is_deleted)
        )
        return list(result.scalars())

    async def update(self, spec_id: str, updates: dict) -> AgreementSpec | None:
        await self._session.execute(update(AgreementSpec).where(AgreementSpec.id == uuid.UUID(spec_id)).values(**updates))
        return await self.get_by_id(spec_id)

    async def soft_delete(self, spec_id: str) -> None:
        await self._session.execute(update(AgreementSpec).where(AgreementSpec.id == uuid.UUID(spec_id)).values(is_deleted=True))


class AgreementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, agreement: Agreement) -> Agreement:
        self._session.add(agreement)
        await self._session.flush()
        return agreement

    async def get_by_id(self, agreement_id: str) -> Agreement | None:
        result = await self._session.execute(select(Agreement).where(Agreement.id == uuid.UUID(agreement_id)))
        return result.scalar_one_or_none()

    async def get_active_for_party(self, party_id: str, tenant_id: str) -> Agreement | None:
        result = await self._session.execute(
            select(Agreement).where(
                Agreement.party_id == uuid.UUID(party_id),
                Agreement.tenant_id == tenant_id,
                Agreement.status == "ACTIVE",
            )
        )
        return result.scalar_one_or_none()

    async def list_with_filters(self, tenant_id: str, party_id: str | None = None, status: str | None = None) -> list[Agreement]:
        q = select(Agreement).where(Agreement.tenant_id == tenant_id)
        if party_id:
            q = q.where(Agreement.party_id == uuid.UUID(party_id))
        if status:
            q = q.where(Agreement.status == status)
        result = await self._session.execute(q)
        return list(result.scalars())

    async def update_status(self, agreement_id: str, status: str) -> None:
        await self._session.execute(update(Agreement).where(Agreement.id == uuid.UUID(agreement_id)).values(status=status))


class CommissionRuleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, rule: CommissionRule) -> CommissionRule:
        self._session.add(rule)
        await self._session.flush()
        return rule

    async def get_by_id(self, rule_id: str) -> CommissionRule | None:
        result = await self._session.execute(select(CommissionRule).where(CommissionRule.id == uuid.UUID(rule_id), ~CommissionRule.is_deleted))
        return result.scalar_one_or_none()

    async def list_for_spec(self, agreement_spec_id: str) -> list[CommissionRule]:
        result = await self._session.execute(
            select(CommissionRule).where(
                CommissionRule.agreement_spec_id == uuid.UUID(agreement_spec_id),
                ~CommissionRule.is_deleted,
            ).order_by(CommissionRule.priority)
        )
        return list(result.scalars())

    async def soft_delete(self, rule_id: str) -> None:
        await self._session.execute(update(CommissionRule).where(CommissionRule.id == uuid.UUID(rule_id)).values(is_deleted=True))
