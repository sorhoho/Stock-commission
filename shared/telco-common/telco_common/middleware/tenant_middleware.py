"""Extracts tenantId from JWT claim and adds to request state."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Kong injects X-Tenant-ID header after validating JWT
        tenant_id = request.headers.get("X-Tenant-ID", "")
        request.state.tenant_id = tenant_id
        response = await call_next(request)
        return response
