"""JWT Bearer dependency — validates Keycloak-issued JWT tokens."""

from __future__ import annotations

import os
from typing import Annotated, Any

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from telco_common.exceptions import UnauthorizedException

_bearer = HTTPBearer(auto_error=False)
_jwks_cache: dict[str, Any] = {}

# When SKIP_AUTH=true, bypass JWT validation (dev/QA only — never set in production).
_SKIP_AUTH = os.getenv("SKIP_AUTH", "").lower() in ("true", "1", "yes")


class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    preferred_username: str | None = None
    realm_access: dict[str, list[str]] = {}
    resource_access: dict[str, Any] = {}
    scope: str = ""


async def _get_jwks(jwks_uri: str) -> dict[str, Any]:
    if jwks_uri not in _jwks_cache:
        async with httpx.AsyncClient() as client:
            resp = await client.get(jwks_uri, timeout=10.0)
            resp.raise_for_status()
            _jwks_cache[jwks_uri] = resp.json()
    return _jwks_cache[jwks_uri]


def require_auth(required_scopes: list[str] | None = None):
    """FastAPI dependency factory — validates JWT and optionally checks scopes."""

    async def _dependency(
        request: Request,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    ) -> TokenPayload:
        from telco_common.config import CommonSettings

        settings = CommonSettings()  # type: ignore[call-arg]

        if _SKIP_AUTH:
            tenant_id = request.headers.get("X-Tenant-ID", "tenant-demo")
            return TokenPayload(
                sub="dev-user",
                tenant_id=tenant_id,
                preferred_username="dev-user",
            )

        if credentials is None:
            raise UnauthorizedException("Missing Authorization header")

        token = credentials.credentials
        try:
            jwks = await _get_jwks(settings.keycloak_jwks_uri)
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience=settings.keycloak_audience,
                options={"verify_exp": True},
            )
        except JWTError as exc:
            raise UnauthorizedException(f"Invalid token: {exc}") from exc

        # Enforce required scopes
        if required_scopes:
            token_scopes = set(payload.get("scope", "").split())
            missing = set(required_scopes) - token_scopes
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required scopes: {missing}",
                )

        return TokenPayload(
            sub=payload["sub"],
            tenant_id=payload.get("tenant_id", ""),
            preferred_username=payload.get("preferred_username"),
            realm_access=payload.get("realm_access", {}),
            resource_access=payload.get("resource_access", {}),
            scope=payload.get("scope", ""),
        )

    return _dependency


CurrentUser = Annotated[TokenPayload, Depends(require_auth())]
