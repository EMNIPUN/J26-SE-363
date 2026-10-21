"""Service-to-service authentication for the AI Backend.

The AI Backend is internal: only the Core API calls it, and it trusts the
`requester` the Core API puts in each request. So every call must carry the
shared secret in the `X-Internal-Token` header, otherwise anyone who can reach
the port could claim to be any user with any role.

Set the same random value in both services:
    AI_BACKEND_INTERNAL_TOKEN=<long random string>
    (generate one: python -c "import secrets; print(secrets.token_urlsafe(48))")
"""

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import settings


def require_internal_token(
    x_internal_token: Annotated[str | None, Header()] = None,
) -> None:
    expected = settings.INTERNAL_TOKEN
    if not expected:
        # Fail closed: an unconfigured service must not run open.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal service token is not configured",
        )
    if x_internal_token is None or not secrets.compare_digest(
        x_internal_token.encode(), expected.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal token",
        )
