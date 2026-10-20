"""The GitHub App client with GitHub replaced by a fake: tokens, repositories, permissions, the sign-in of a person, and the signed state."""
import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from shared.github_app import GitHubApp, GitHubAppConfig, GitHubAppError, noreply_emails, read_state, sign_state, strongest

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE = KEY.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
PUBLIC = KEY.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
CONFIG = GitHubAppConfig(app_id="123", slug="selvia-test", client_id="Iv1.abc", client_secret="sec", private_key=PRIVATE, state_secret="state-secret")


def fake_github(calls):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path, request.headers.get("authorization", "")[:12]))
        path = request.url.path
        if path == "/app/installations/7/access_tokens":
            claims = jwt.decode(request.headers["authorization"].split()[1], PUBLIC, algorithms=["RS256"])
            assert claims["iss"] == "123" and claims["exp"] - claims["iat"] <= 600
            return httpx.Response(201, json={"token": "ghs_installation", "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 3600))})
        if path == "/installation/repositories":
            return httpx.Response(200, json={"repositories": [{"id": 1, "full_name": "acme/app", "private": True, "default_branch": "main"}, {"id": 2, "full_name": "acme/docs", "private": False}]})
        if path == "/repos/acme/app/collaborators/ann/permission":
            return httpx.Response(200, json={"permission": "write"})
        if path == "/repos/acme/app/collaborators/bob/permission":
            return httpx.Response(200, json={"permission": "read"})
        if path == "/repos/acme/app/collaborators/stranger/permission":
            return httpx.Response(404, json={"message": "Not Found"})
        if path == "/login/oauth/access_token":
            return httpx.Response(200, json={"access_token": "ghu_user"} if b"good-code" in request.content else {"error": "bad_verification_code"})
        if path == "/user":
            return httpx.Response(200, json={"id": 4242, "login": "Ann-Dev", "avatar_url": "https://a/x.png"})
        return httpx.Response(500)
    return handler


@pytest.fixture()
def app_and_calls():
    calls = []
    return GitHubApp(CONFIG, client=httpx.Client(transport=httpx.MockTransport(fake_github(calls)))), calls


def test_configuration_comes_from_the_environment_and_a_key_file(tmp_path):
    key = tmp_path / "app.pem"
    key.write_text(PRIVATE)
    cfg = GitHubAppConfig.from_env({"GITHUB_APP_ID": "1", "GITHUB_APP_SLUG": "s", "GITHUB_APP_CLIENT_ID": "c", "GITHUB_APP_CLIENT_SECRET": "x", "GITHUB_APP_PRIVATE_KEY_PATH": str(key)})
    assert cfg.configured and cfg.private_key.startswith("-----BEGIN") and cfg.state_secret == "x"
    assert not GitHubAppConfig.from_env({}).configured
    with pytest.raises(GitHubAppError):
        GitHubApp(GitHubAppConfig()).app_jwt()


def test_an_installation_token_is_fetched_once_and_reused(app_and_calls):
    app, calls = app_and_calls
    assert app.installation_token(7) == "ghs_installation" == app.installation_token(7)
    assert sum(1 for c in calls if c[1].endswith("access_tokens")) == 1


def test_repositories_and_permissions(app_and_calls):
    app, _ = app_and_calls
    assert [r["full_name"] for r in app.installation_repos(7)] == ["acme/app", "acme/docs"]
    assert [app.permission(7, "acme/app", u) for u in ("ann", "bob", "stranger")] == ["write", "read", "none"]
    assert strongest("read", "admin", "write") == "admin" and strongest("maintain", "triage") == "none" and strongest() == "none"


def test_a_person_signs_in_and_github_names_the_account(app_and_calls):
    app, _ = app_and_calls
    url = app.authorize_url("STATE", "http://localhost/cb")
    assert url.startswith("https://github.com/login/oauth/authorize?") and "client_id=Iv1.abc" in url and "state=STATE" in url
    token = app.exchange_code("good-code", "http://localhost/cb")
    assert app.user(token) == {"id": 4242, "login": "ann-dev", "avatar_url": "https://a/x.png"}  # the login is lower case, as the platform stores it
    with pytest.raises(GitHubAppError):
        app.exchange_code("wrong", "http://localhost/cb")


def test_github_errors_do_not_leak_tokens(app_and_calls):
    app, _ = app_and_calls
    with pytest.raises(GitHubAppError) as e:
        app.installation_token(99)
    assert "ghs_" not in str(e.value) and "BEGIN" not in str(e.value)


def test_noreply_addresses_and_signed_state():
    assert noreply_emails(4242, "ann-dev") == ["4242+ann-dev@users.noreply.github.com", "ann-dev@users.noreply.github.com"]
    token = sign_state("s", {"user": "u1", "team": "T"})
    assert read_state("s", token)["user"] == "u1"
    with pytest.raises(GitHubAppError):
        read_state("other", token)
    with pytest.raises(GitHubAppError):
        read_state("s", sign_state("s", {"user": "u1"}, ttl=-5))
