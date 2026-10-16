"""Authenticate trusted Core API callers to the AI Backend orchestration API.

Uses a dedicated shared service credential (AI_BACKEND_INTERNAL_TOKEN), separate from
Keycloak login tokens and short-lived tutor MCP tokens. Never logs Authorization
headers or secrets.
"""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_internal_service(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> None:
    """Reject callers that lack a valid Core API service Bearer token."""
    if not settings.internal_service_auth_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal service authentication is not configured",
        )

    expected = settings.INTERNAL_TOKEN
    assert expected is not None

    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise _unauthorized()

    provided = credentials.credentials
    provided_bytes = provided.encode("utf-8")
    expected_bytes = expected.encode("utf-8")
    # compare_digest requires equal length; unequal length is an auth failure, not an error.
    if len(provided_bytes) != len(expected_bytes) or not hmac.compare_digest(
        provided_bytes, expected_bytes
    ):
        raise _unauthorized()
