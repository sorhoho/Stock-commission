from __future__ import annotations
from collections.abc import AsyncGenerator
from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db.session import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_current_tenant_id(request: Request) -> str:
    """Tenant from the X-Tenant-ID header (set on request.state by TenantMiddleware).

    Used by internal service-to-service endpoints that are called by other
    services on the trusted internal network rather than by external clients,
    so they authenticate via the tenant header instead of a user JWT.
    """
    tenant_id: str = getattr(request.state, "tenant_id", "")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Tenant-ID header",
        )
    return tenant_id
