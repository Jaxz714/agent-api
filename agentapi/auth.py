"""API key authentication middleware."""

from __future__ import annotations

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from agentapi.models import AuthConfig


def create_auth_dependency(config: AuthConfig):
    """Create a FastAPI dependency that enforces API key auth."""

    if not config.enabled:
        # Auth disabled — return a no-op dependency
        async def no_auth() -> None:
            return None
        return no_auth

    api_key_header = APIKeyHeader(name=config.header_name, auto_error=False)

    async def verify_api_key(
        api_key: str | None = Security(api_key_header),
    ) -> str:
        if api_key is None:
            raise HTTPException(
                status_code=401,
                detail=f"Missing API key. Send it via the '{config.header_name}' header.",
            )
        if api_key not in config.api_keys:
            raise HTTPException(status_code=403, detail="Invalid API key.")
        return api_key

    return verify_api_key
