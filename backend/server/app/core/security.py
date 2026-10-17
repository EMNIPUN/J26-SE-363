"""Keycloak authentication for the Core API.

The frontend logs in with Keycloak (realm "mentor", client "mentor-frontend")
and sends the access token as `Authorization: Bearer <token>`. Protected
endpoints verify it here: RS256 signature against the realm's public keys,
expiry, issuer, and the client the token was issued to (`azp`).

    @router.get("/something")
    def endpoint(user: Annotated[CurrentUser, Depends(get_current_user)]): ...

    @router.post("/lecturer-only", dependencies=[Depends(require_roles(UserRole.LECTURER))])
"""

from collections.abc import Callable, Iterable
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from shared.contracts import RequesterContext, UserRole

from app.core.config import settings

ROLE_PRIORITY = (UserRole.ADMIN, UserRole.LECTURER, UserRole.STUDENT)
ROLE_ALIASES = {"instructor": UserRole.LECTURER}
CLOCK_SKEW_SECONDS = 30

KeyResolver = Callable[[str], Any]


class CurrentUser(BaseModel):
    user_id: str
    username: str | None = None
    name: str | None = None
    email: str | None = None
    role: UserRole
    roles: list[str] = []

    def to_requester(self) -> RequesterContext:
        return RequesterContext(user_id=self.user_id, role=self.role)


def primary_role(realm_roles: Iterable[str]) -> UserRole:
    """admin > lecturer > student.

    Users without a SELVIA role are students: self-registered accounts only
    receive Keycloak's default roles. This matches the frontend's resolveRole().
    """
    known = {role.value for role in UserRole}
    found = {ROLE_ALIASES.get(r) or (UserRole(r) if r in known else None) for r in realm_roles}
    return next((role for role in ROLE_PRIORITY if role in found), UserRole.STUDENT)


class AuthenticationError(Exception):
    """The token is missing, invalid, expired or issued for another realm/client."""


class AuthServiceUnavailable(Exception):
    """Keycloak's public keys could not be fetched."""


class TokenVerifier:
    def __init__(
        self,
        issuer: str,
        allowed_clients: Iterable[str],
        key_resolver: KeyResolver,
    ):
        self._issuer = issuer
        self._allowed_clients = frozenset(allowed_clients)
        self._key_resolver = key_resolver

    def verify(self, token: str) -> CurrentUser:
        try:
            key = self._key_resolver(token)
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self._issuer,
                leeway=CLOCK_SKEW_SECONDS,
                options={"verify_aud": False, "require": ["exp", "iat", "iss", "sub"]},
            )
        except jwt.PyJWKClientConnectionError as exc:
            raise AuthServiceUnavailable(str(exc)) from exc
        except (jwt.InvalidTokenError, jwt.PyJWKClientError) as exc:
            raise AuthenticationError(str(exc)) from exc

        if claims.get("azp") not in self._allowed_clients:
            raise AuthenticationError(f"Token was issued to client {claims.get('azp')!r}")

        realm_roles = claims.get("realm_access", {}).get("roles", [])
        return CurrentUser(
            user_id=claims["sub"],
            username=claims.get("preferred_username"),
            name=claims.get("name"),
            email=claims.get("email"),
            role=primary_role(realm_roles),
            roles=realm_roles,
        )


def jwks_key_resolver(jwks_url: str) -> KeyResolver:
    client = jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
    return lambda token: client.get_signing_key_from_jwt(token).key


@lru_cache
def get_token_verifier() -> TokenVerifier:
    return TokenVerifier(
        issuer=settings.keycloak_issuer,
        allowed_clients=settings.KEYCLOAK_ALLOWED_CLIENTS,
        key_resolver=jwks_key_resolver(settings.keycloak_jwks_url),
    )


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> CurrentUser:
    # Sync on purpose: fetching Keycloak keys is blocking, so FastAPI runs this in a thread.
    if credentials is None:
        raise _unauthorized("Not authenticated")
    try:
        return verifier.verify(credentials.credentials)
    except AuthenticationError as exc:
        raise _unauthorized("Invalid or expired token") from exc
    except AuthServiceUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc


def require_roles(*roles: UserRole) -> Callable[[CurrentUser], CurrentUser]:
    def check_role(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        return user

    return check_role


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
