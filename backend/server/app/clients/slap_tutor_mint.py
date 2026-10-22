"""HTTP client: Core API -> SLAP internal tutor-access-token mint.

Mints short-lived opaque tutor MCP tokens using the shared INTERNAL_TUTOR_MINT_TOKEN.
Callers must pass the validated Keycloak issuer (settings.keycloak_issuer) and subject
(CurrentUser.user_id). Never log Authorization headers, tokens, or response bodies.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import settings

MINT_PATH = "/api/v1/internal/tutor-access-tokens"


class SlapTutorMintError(Exception):
    """Base error for SLAP tutor token minting. Messages must never contain secrets."""


class SlapTutorMintConfigError(SlapTutorMintError):
    """SLAP mint URL or internal credential is missing or invalid."""


class SlapTutorMintAuthError(SlapTutorMintError):
    """SLAP rejected the internal mint credential (401/403)."""


class SlapTutorMintIdentityNotFoundError(SlapTutorMintError):
    """No active admin-verified external identity link for the issuer/subject (404)."""


class SlapTutorMintUnavailableError(SlapTutorMintError):
    """SLAP reported minting temporarily unavailable (503)."""


class SlapTutorMintTimeoutError(SlapTutorMintError):
    """The mint request timed out."""


class SlapTutorMintNetworkError(SlapTutorMintError):
    """Network failure talking to SLAP (excluding timeouts)."""


class SlapTutorMintProtocolError(SlapTutorMintError):
    """Unexpected status or response shape from SLAP."""


class _TutorAccessTokenData(BaseModel):
    """Inner payload of SLAP's `{ success, data }` mint response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    access_token: str = Field(alias="accessToken", min_length=1)
    token_type: str = Field(alias="tokenType", min_length=1)
    expires_in: int = Field(alias="expiresIn", gt=0)
    expires_at: int = Field(alias="expiresAt")
    resource: str = Field(min_length=1)


class _MintSuccessEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")

    success: bool
    data: _TutorAccessTokenData


@dataclass(frozen=True, slots=True)
class TutorAccessToken:
    """Opaque tutor MCP access token returned to a trusted Core API caller only."""

    access_token: str
    token_type: str
    expires_in: int
    expires_at: int
    resource: str


class SlapTutorMintClient:
    """POST /api/v1/internal/tutor-access-tokens against SLAP.

    The mint method accepts only issuer and subject keyword arguments. Scopes and
    platform UUIDs are fixed/resolved on SLAP and are not accepted here.
    """

    def __init__(
        self,
        base_url: str,
        mint_token: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if not base_url or not base_url.strip():
            raise SlapTutorMintConfigError("SLAP_BASE_URL is not configured")
        if not mint_token or not mint_token.strip():
            raise SlapTutorMintConfigError("INTERNAL_TUTOR_MINT_TOKEN is not configured")
        if timeout_seconds <= 0:
            raise SlapTutorMintConfigError("SLAP_TUTOR_MINT_TIMEOUT_SECONDS must be positive")

        self._base_url = base_url.rstrip("/")
        self._mint_token = mint_token
        self._timeout = timeout_seconds
        self._transport = transport

    async def mint_tutor_access_token(
        self,
        *,
        issuer: str,
        subject: str,
    ) -> TutorAccessToken:
        """Mint a short-lived tutor MCP token for the given Keycloak identity.

        Pass ``settings.keycloak_issuer`` and ``CurrentUser.user_id`` from the
        authenticated Core API request. Omits ``expiresInSeconds`` so SLAP applies
        its default short lifetime.
        """
        if not isinstance(issuer, str) or not issuer.strip():
            raise SlapTutorMintConfigError("issuer must be a non-empty string")
        if not isinstance(subject, str) or not subject.strip():
            raise SlapTutorMintConfigError("subject must be a non-empty string")

        headers = {
            "Authorization": f"Bearer {self._mint_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        body = {"issuer": issuer.strip(), "subject": subject.strip()}

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
                trust_env=False,
            ) as client:
                response = await client.post(MINT_PATH, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            raise SlapTutorMintTimeoutError("SLAP tutor token mint request timed out") from exc
        except httpx.HTTPError as exc:
            raise SlapTutorMintNetworkError("SLAP tutor token mint request failed") from exc

        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> TutorAccessToken:
        status = response.status_code

        if status == 401 or status == 403:
            raise SlapTutorMintAuthError(
                "SLAP rejected the internal tutor mint credential"
            )
        if status == 404:
            raise SlapTutorMintIdentityNotFoundError(
                "SLAP external identity link not found for the given issuer and subject"
            )
        if status == 503:
            raise SlapTutorMintUnavailableError(
                "SLAP tutor token minting is temporarily unavailable"
            )
        if status < 200 or status >= 300:
            raise SlapTutorMintProtocolError(
                f"SLAP tutor token mint returned unexpected status {status}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise SlapTutorMintProtocolError(
                "SLAP tutor token mint returned a non-JSON response"
            ) from exc

        try:
            envelope = _MintSuccessEnvelope.model_validate(payload)
        except ValidationError as exc:
            raise SlapTutorMintProtocolError(
                "SLAP tutor token mint returned an invalid response shape"
            ) from exc

        if not envelope.success:
            raise SlapTutorMintProtocolError(
                "SLAP tutor token mint returned success=false"
            )

        data = envelope.data
        return TutorAccessToken(
            access_token=data.access_token,
            token_type=data.token_type,
            expires_in=data.expires_in,
            expires_at=data.expires_at,
            resource=data.resource,
        )


def get_slap_tutor_mint_client() -> SlapTutorMintClient:
    """Build a client from settings; fails closed when mint config is incomplete."""
    if not settings.slap_tutor_mint_configured:
        raise SlapTutorMintConfigError(
            "SLAP tutor token minting is not configured "
            "(set SLAP_BASE_URL and INTERNAL_TUTOR_MINT_TOKEN)"
        )
    assert settings.SLAP_BASE_URL is not None
    assert settings.INTERNAL_TUTOR_MINT_TOKEN is not None
    return SlapTutorMintClient(
        settings.SLAP_BASE_URL,
        settings.INTERNAL_TUTOR_MINT_TOKEN,
        settings.SLAP_TUTOR_MINT_TIMEOUT_SECONDS,
    )
