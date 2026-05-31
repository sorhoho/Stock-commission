"""PartyCharacteristic API endpoints."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbSession, TenantId, get_current_tenant_id, get_db
from app.domain.models import PartyCharacteristic, PartyCharacteristicCreate
from app.infrastructure.db import models as orm
from telco_common.exceptions import NotFoundException

router = APIRouter(prefix="/partyCharacteristic", tags=["PartyCharacteristic"])


@router.get("/", response_model=list[PartyCharacteristic])
async def list_characteristics(
    party_id: uuid.UUID,
    tenant_id: TenantId = Depends(get_current_tenant_id),
    db: DbSession = Depends(get_db),
) -> list[PartyCharacteristic]:
    """List all characteristics for a party."""
    result = await db.execute(
        select(orm.PartyCharacteristic).where(
            orm.PartyCharacteristic.party_id == party_id,
            orm.PartyCharacteristic.tenant_id == tenant_id,
        )
    )
    items = result.scalars().all()
    out = []
    for item in items:
        # Deserialise stored JSON value back to Python object
        try:
            value = json.loads(item.value)
        except (json.JSONDecodeError, TypeError):
            value = item.value
        out.append(
            PartyCharacteristic(
                id=item.id,
                party_id=item.party_id,
                name=item.name,
                value=value,
                value_type=item.value_type,
            )
        )
    return out


@router.post("/", response_model=PartyCharacteristic, status_code=status.HTTP_201_CREATED)
async def create_characteristic(
    body: PartyCharacteristicCreate,
    tenant_id: TenantId = Depends(get_current_tenant_id),
    db: DbSession = Depends(get_db),
) -> PartyCharacteristic:
    """Add a characteristic to a party."""
    # Verify party exists in this tenant
    party_result = await db.execute(
        select(orm.Party).where(
            orm.Party.id == body.party_id,
            orm.Party.tenant_id == tenant_id,
        )
    )
    if party_result.scalar_one_or_none() is None:
        raise NotFoundException("Party", str(body.party_id))

    # Serialise value to JSON string for storage
    stored_value = json.dumps(body.value)

    char = orm.PartyCharacteristic(
        party_id=body.party_id,
        name=body.name,
        value=stored_value,
        value_type=body.value_type,
        tenant_id=tenant_id,
    )
    db.add(char)
    await db.flush()
    await db.refresh(char)

    return PartyCharacteristic(
        id=char.id,
        party_id=char.party_id,
        name=char.name,
        value=body.value,
        value_type=char.value_type,
    )


@router.delete("/{characteristic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_characteristic(
    characteristic_id: uuid.UUID,
    tenant_id: TenantId = Depends(get_current_tenant_id),
    db: DbSession = Depends(get_db),
) -> None:
    """Delete a party characteristic."""
    result = await db.execute(
        select(orm.PartyCharacteristic).where(
            orm.PartyCharacteristic.id == characteristic_id,
            orm.PartyCharacteristic.tenant_id == tenant_id,
        )
    )
    char = result.scalar_one_or_none()
    if char is None:
        raise NotFoundException("PartyCharacteristic", str(characteristic_id))
    await db.delete(char)
