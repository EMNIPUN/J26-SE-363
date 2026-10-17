import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from procrastinate.testing import InMemoryConnector
from shared.contracts import RequesterContext, UserRole
from shared.queue import app as procrastinate_app

from app.core.config import Settings, settings
from app.core.security import (
    AuthenticationError,
    AuthServiceUnavailable,
    CurrentUser,
    TokenVerifier,
    get_token_verifier,
    primary_role,
)
from app.main import app

ISSUER = "http://localhost:8000/auth/realms/mentor"
SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_token(key=SIGNING_KEY, **overrides) -> str:
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "sub": "kc-user-1",
        "azp": "mentor-frontend",
        "iat": now,
        "exp": now + 300,
        "preferred_username": "it21000001",
        "name": "Nimal Perera",
        "email": "nimal@example.com",
        "realm_access": {"roles": ["default-roles-mentor", "student"]},
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "test-key"})


def make_verifier(resolver=lambda token: SIGNING_KEY.public_key()) -> TokenVerifier:
    return TokenVerifier(issuer=ISSUER, allowed_clients=["mentor-frontend"], key_resolver=resolver)


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    app.dependency_overrides[get_token_verifier] = make_verifier
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- role mapping -----------------------------------------------------------


@pytest.mark.parametrize(
    ("roles", "expected"),
    [
        (["student"], UserRole.STUDENT),
        (["lecturer"], UserRole.LECTURER),
        (["instructor"], UserRole.LECTURER),
        (["student", "lecturer"], UserRole.LECTURER),
        (["lecturer", "admin"], UserRole.ADMIN),
        (["default-roles-mentor", "offline_access"], UserRole.STUDENT),
        ([], UserRole.STUDENT),
    ],
)
def test_primary_role(roles, expected):
    assert primary_role(roles) is expected


# --- token verification -----------------------------------------------------


def test_valid_token_gives_current_user():
    user = make_verifier().verify(make_token())

    assert user.user_id == "kc-user-1"
    assert user.username == "it21000001"
    assert user.email == "nimal@example.com"
    assert user.role is UserRole.STUDENT
    assert user.to_requester() == RequesterContext(user_id="kc-user-1", role=UserRole.STUDENT)


@pytest.mark.parametrize(
    "token",
    [
        make_token(exp=int(time.time()) - 600),
        make_token(iss="http://evil.example.com/realms/mentor"),
        make_token(azp="some-other-client"),
        make_token(sub=None),
        make_token(key=OTHER_KEY),
        "not-a-jwt",
    ],
    ids=["expired", "wrong-issuer", "wrong-client", "no-subject", "wrong-signature", "garbage"],
)
def test_invalid_tokens_are_rejected(token):
    with pytest.raises(AuthenticationError):
        make_verifier().verify(token)


def test_unreachable_keycloak_is_reported_separately():
    def offline(token):
        raise jwt.PyJWKClientConnectionError("connection refused")

    with pytest.raises(AuthServiceUnavailable):
        make_verifier(offline).verify(make_token())


def test_issuer_and_jwks_url_follow_settings():
    public = Settings(
        _env_file=None, KEYCLOAK_SERVER_URL="http://localhost:8000/auth/", KEYCLOAK_REALM="mentor"
    )
    internal = Settings(
        _env_file=None, KEYCLOAK_JWKS_URL="http://keycloak:8080/auth/realms/mentor/certs"
    )

    assert public.keycloak_issuer == ISSUER
    assert public.keycloak_jwks_url == f"{ISSUER}/protocol/openid-connect/certs"
    assert internal.keycloak_jwks_url == "http://keycloak:8080/auth/realms/mentor/certs"


# --- API --------------------------------------------------------------------


def test_me_requires_a_token(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_rejects_an_invalid_token(client):
    response = client.get("/api/v1/auth/me", headers=auth_header(make_token(key=OTHER_KEY)))

    assert response.status_code == 401


def test_me_returns_the_logged_in_user(client):
    token = make_token(realm_access={"roles": ["lecturer"]})

    response = client.get("/api/v1/auth/me", headers=auth_header(token))

    assert response.status_code == 200
    user = CurrentUser.model_validate(response.json())
    assert user.user_id == "kc-user-1"
    assert user.role is UserRole.LECTURER


def test_me_reports_keycloak_outage_as_503(client):
    def offline(token):
        raise jwt.PyJWKClientConnectionError("connection refused")

    app.dependency_overrides[get_token_verifier] = lambda: make_verifier(offline)

    response = client.get("/api/v1/auth/me", headers=auth_header(make_token()))

    assert response.status_code == 503


@pytest.mark.parametrize(
    ("headers", "expected_status"),
    [
        ({}, 401),
        (auth_header(make_token()), 403),
        (auth_header(make_token(realm_access={"roles": ["lecturer"]})), 403),
    ],
    ids=["anonymous", "student", "lecturer"],
)
def test_jobs_api_is_admin_only(client, headers, expected_status):
    response = client.post("/api/v1/jobs", json={"task_name": "x.y"}, headers=headers)

    assert response.status_code == expected_status


def test_admin_can_publish_a_job(client):
    token = make_token(realm_access={"roles": ["admin"]})

    with procrastinate_app.replace_connector(InMemoryConnector()):
        response = client.post(
            "/api/v1/jobs",
            json={"task_name": "performance.assess_student", "queue": "performance"},
            headers=auth_header(token),
        )

    assert response.status_code == 202


def test_cors_allows_only_configured_origins(client):
    preflight = {"Access-Control-Request-Method": "GET"}
    frontend = settings.CORS_ORIGINS[0]

    allowed = client.options("/api/v1/auth/me", headers={**preflight, "Origin": frontend})
    blocked = client.options(
        "/api/v1/auth/me", headers={**preflight, "Origin": "http://evil.example.com"}
    )

    assert allowed.headers.get("access-control-allow-origin") == frontend
    assert "access-control-allow-origin" not in blocked.headers
