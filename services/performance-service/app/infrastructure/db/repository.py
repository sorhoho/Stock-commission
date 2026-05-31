"""Repository layer for the Performance service."""

from __future__ import annotations

import uuid
from datetime import date

import structlog
from sqlalchemy import and_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    PerformanceIndicatorSpec,
    PerformanceIndicatorSpecCreate,
    PerformanceIndicatorSpecUpdate,
    PerformanceMeasurement,
    PerformanceTarget,
    PerformanceTargetCreate,
    PerformanceTargetUpdate,
    TargetStatus,
)
from app.infrastructure.db.models import (
    PerformanceIndicatorSpecDB,
    PerformanceMeasurementDB,
    PerformanceTargetDB,
)

log = structlog.get_logger(__name__)


class IndicatorSpecRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        data: PerformanceIndicatorSpecCreate,
        tenant_id: str,
    ) -> PerformanceIndicatorSpec:
        db_obj = PerformanceIndicatorSpecDB(
            name=data.name,
            description=data.description,
            unit_of_measure=data.unit_of_measure,
            indicator_type=data.indicator_type,
            measurement_interval=data.measurement_interval,
            tenant_id=tenant_id,
        )
        self._session.add(db_obj)
        await self._session.flush()
        await self._session.refresh(db_obj)
        log.info("indicator_spec.created", spec_id=str(db_obj.id))
        return PerformanceIndicatorSpec.model_validate(db_obj)

    async def get_by_id(
        self, spec_id: uuid.UUID, tenant_id: str
    ) -> PerformanceIndicatorSpec | None:
        result = await self._session.execute(
            select(PerformanceIndicatorSpecDB).where(
                PerformanceIndicatorSpecDB.id == spec_id,
                PerformanceIndicatorSpecDB.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        return PerformanceIndicatorSpec.model_validate(row) if row else None

    async def list_all(self, tenant_id: str) -> list[PerformanceIndicatorSpec]:
        result = await self._session.execute(
            select(PerformanceIndicatorSpecDB).where(
                PerformanceIndicatorSpecDB.tenant_id == tenant_id
            )
        )
        return [
            PerformanceIndicatorSpec.model_validate(r) for r in result.scalars().all()
        ]

    async def update(
        self,
        spec_id: uuid.UUID,
        data: PerformanceIndicatorSpecUpdate,
        tenant_id: str,
    ) -> PerformanceIndicatorSpec | None:
        patch = data.model_dump(exclude_none=True)
        if not patch:
            return await self.get_by_id(spec_id, tenant_id)
        await self._session.execute(
            update(PerformanceIndicatorSpecDB)
            .where(
                PerformanceIndicatorSpecDB.id == spec_id,
                PerformanceIndicatorSpecDB.tenant_id == tenant_id,
            )
            .values(**patch)
        )
        return await self.get_by_id(spec_id, tenant_id)


class TargetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        data: PerformanceTargetCreate,
        tenant_id: str,
    ) -> PerformanceTarget:
        db_obj = PerformanceTargetDB(
            party_id=data.party_id,
            kpi_spec_id=data.kpi_spec_id,
            target_value=data.target_value,
            period_start=data.period_start,
            period_end=data.period_end,
            status=TargetStatus.ACTIVE,
            tenant_id=tenant_id,
        )
        self._session.add(db_obj)
        await self._session.flush()
        await self._session.refresh(db_obj)
        log.info("target.created", target_id=str(db_obj.id))
        return PerformanceTarget.model_validate(db_obj)

    async def get_by_id(
        self, target_id: uuid.UUID, tenant_id: str
    ) -> PerformanceTarget | None:
        result = await self._session.execute(
            select(PerformanceTargetDB).where(
                PerformanceTargetDB.id == target_id,
                PerformanceTargetDB.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        return PerformanceTarget.model_validate(row) if row else None

    async def list_for_party(
        self,
        party_id: uuid.UUID,
        tenant_id: str,
        period: date | None = None,
    ) -> list[PerformanceTarget]:
        conditions = [
            PerformanceTargetDB.party_id == party_id,
            PerformanceTargetDB.tenant_id == tenant_id,
        ]
        if period:
            conditions.append(PerformanceTargetDB.period_start <= period)
            conditions.append(PerformanceTargetDB.period_end >= period)
        result = await self._session.execute(
            select(PerformanceTargetDB).where(and_(*conditions))
        )
        return [PerformanceTarget.model_validate(r) for r in result.scalars().all()]

    async def update(
        self,
        target_id: uuid.UUID,
        data: PerformanceTargetUpdate,
        tenant_id: str,
    ) -> PerformanceTarget | None:
        patch = data.model_dump(exclude_none=True)
        if not patch:
            return await self.get_by_id(target_id, tenant_id)
        await self._session.execute(
            update(PerformanceTargetDB)
            .where(
                PerformanceTargetDB.id == target_id,
                PerformanceTargetDB.tenant_id == tenant_id,
            )
            .values(**patch)
        )
        return await self.get_by_id(target_id, tenant_id)

    async def update_status(
        self,
        target_id: uuid.UUID,
        status: TargetStatus,
        tenant_id: str,
    ) -> None:
        await self._session.execute(
            update(PerformanceTargetDB)
            .where(
                PerformanceTargetDB.id == target_id,
                PerformanceTargetDB.tenant_id == tenant_id,
            )
            .values(status=status)
        )
        log.info("target.status_updated", target_id=str(target_id), status=status)

    async def get_active_for_party_and_spec(
        self,
        party_id: uuid.UUID,
        kpi_spec_id: uuid.UUID,
        period: date,
        tenant_id: str,
    ) -> list[PerformanceTarget]:
        result = await self._session.execute(
            select(PerformanceTargetDB).where(
                PerformanceTargetDB.party_id == party_id,
                PerformanceTargetDB.kpi_spec_id == kpi_spec_id,
                PerformanceTargetDB.tenant_id == tenant_id,
                PerformanceTargetDB.status == TargetStatus.ACTIVE,
                PerformanceTargetDB.period_start <= period,
                PerformanceTargetDB.period_end >= period,
            )
        )
        return [PerformanceTarget.model_validate(r) for r in result.scalars().all()]


class MeasurementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        party_id: uuid.UUID,
        kpi_spec_id: uuid.UUID,
        period: date,
        measured_value: float,
        source_event_id: str,
        tenant_id: str,
    ) -> PerformanceMeasurement:
        """Upsert a measurement — increments value and appends source event id."""
        existing = await self._get_by_party_spec_period(
            party_id, kpi_spec_id, period, tenant_id
        )
        if existing:
            new_value = existing.measured_value + measured_value
            new_sources = list(set(existing.source_event_ids + [source_event_id]))
            await self._session.execute(
                update(PerformanceMeasurementDB)
                .where(PerformanceMeasurementDB.id == existing.id)
                .values(measured_value=new_value, source_event_ids=new_sources)
            )
            refreshed = await self._get_by_id_raw(existing.id)
            assert refreshed is not None
            return PerformanceMeasurement.model_validate(refreshed)

        db_obj = PerformanceMeasurementDB(
            party_id=party_id,
            kpi_spec_id=kpi_spec_id,
            period=period,
            measured_value=measured_value,
            source_event_ids=[source_event_id],
            tenant_id=tenant_id,
        )
        self._session.add(db_obj)
        await self._session.flush()
        await self._session.refresh(db_obj)
        log.info(
            "measurement.upserted",
            party_id=str(party_id),
            kpi_spec_id=str(kpi_spec_id),
            period=str(period),
        )
        return PerformanceMeasurement.model_validate(db_obj)

    async def list_with_filters(
        self,
        tenant_id: str,
        party_id: uuid.UUID | None = None,
        kpi_spec_id: uuid.UUID | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[PerformanceMeasurement]:
        conditions = [PerformanceMeasurementDB.tenant_id == tenant_id]
        if party_id:
            conditions.append(PerformanceMeasurementDB.party_id == party_id)
        if kpi_spec_id:
            conditions.append(PerformanceMeasurementDB.kpi_spec_id == kpi_spec_id)
        if from_date:
            conditions.append(PerformanceMeasurementDB.period >= from_date)
        if to_date:
            conditions.append(PerformanceMeasurementDB.period <= to_date)
        result = await self._session.execute(
            select(PerformanceMeasurementDB).where(and_(*conditions))
        )
        return [
            PerformanceMeasurement.model_validate(r) for r in result.scalars().all()
        ]

    async def _get_by_party_spec_period(
        self,
        party_id: uuid.UUID,
        kpi_spec_id: uuid.UUID,
        period: date,
        tenant_id: str,
    ) -> PerformanceMeasurement | None:
        result = await self._session.execute(
            select(PerformanceMeasurementDB).where(
                PerformanceMeasurementDB.party_id == party_id,
                PerformanceMeasurementDB.kpi_spec_id == kpi_spec_id,
                PerformanceMeasurementDB.period == period,
                PerformanceMeasurementDB.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        return PerformanceMeasurement.model_validate(row) if row else None

    async def _get_by_id_raw(
        self, measurement_id: uuid.UUID
    ) -> PerformanceMeasurementDB | None:
        result = await self._session.execute(
            select(PerformanceMeasurementDB).where(
                PerformanceMeasurementDB.id == measurement_id
            )
        )
        return result.scalar_one_or_none()
