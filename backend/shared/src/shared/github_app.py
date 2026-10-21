"""GitHub App access, shared by the Core API (linking repositories and people) and the worker (reading and cloning a team's repository).

One GitHub App does two jobs:
  * Installed on a repository by the team leader, it gives the system a short-lived token for that repository only (``installation_token``): read the repository, its pull requests and reviews,
    clone it if it is private, and ask GitHub which permission a login has on it (``permission``).
  * "Request user authorization": a person signs in to GitHub from the system (``authorize_url`` then ``exchange_code`` then ``user``). GitHub itself says which account it is, so a linked login is verified, not typed.
The App's own settings come from the environment (``GitHubAppConfig.from_env``); the private key is read from a file outside the repository (or given inline). Nothing here is ever logged or returned to a browser:
tokens live in memory for less than an hour, the user's access token is used once to read their id and login and is then dropped.
"""
import calendar
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

API = "https://api.github.com"
WEB = "https://github.com"
PERMISSIONS = ("none", "read", "write", "admin")  # in order of strength; GitHub's "maintain" counts as write and "triage" as read


class GitHubAppError(RuntimeError):
    """GitHub refused, or the App is not configured. The message never contains a token or a key."""


@dataclass
class GitHubAppConfig:
    app_id: str = ""
    slug: str = ""
    client_id: str = ""
    client_secret: str = ""
    private_key: str = ""
    state_secret: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.app_id and self.private_key and self.client_id and self.client_secret and self.slug)

    @classmethod
    def from_env(cls, env=None) -> "GitHubAppConfig":
        env = os.environ if env is None else env
        key = env.get("GITHUB_APP_PRIVATE_KEY", "")
        path = env.get("GITHUB_APP_PRIVATE_KEY_PATH", "")
        if not key and path and Path(path).is_file():
            key = Path(path).read_text(encoding="utf-8")
        key = key.replace("\\n", "\n")
        secret = env.get("GITHUB_STATE_SECRET") or env.get("GITHUB_APP_CLIENT_SECRET", "")
        return cls(app_id=env.get("GITHUB_APP_ID", ""), slug=env.get("GITHUB_APP_SLUG", ""), client_id=env.get("GITHUB_APP_CLIENT_ID", ""), client_secret=env.get("GITHUB_APP_CLIENT_SECRET", ""),
                   private_key=key, state_secret=secret)


def strongest(*levels: str) -> str:
    return max((l for l in levels if l in PERMISSIONS), key=PERMISSIONS.index, default="none")


@dataclass
class GitHubApp:
    config: GitHubAppConfig
    client: httpx.Client | None = None
    _tokens: dict = field(default_factory=dict)

    def _http(self) -> httpx.Client:
        if self.client is None:
            self.client = httpx.Client(timeout=20.0, headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "selvia-github-app"})
        return self.client

    def _need(self):
        if not self.config.configured:
            raise GitHubAppError("the GitHub App is not configured")

    # ---- the App itself ------------------------------------------------------------------------------------------------------------
    def app_jwt(self, now: float | None = None) -> str:
        self._need()
        t = int(now if now is not None else time.time())
        return jwt.encode({"iat": t - 60, "exp": t + 9 * 60, "iss": self.config.app_id}, self.config.private_key, algorithm="RS256")

    def installation_token(self, installation_id: int) -> str:
        """A token for one installation (the repositories the leader chose), cached until five minutes before it expires."""
        cached = self._tokens.get(installation_id)
        if cached and cached[1] - time.time() > 300:
            return cached[0]
        r = self._http().post(f"{API}/app/installations/{installation_id}/access_tokens", headers={"Authorization": f"Bearer {self.app_jwt()}"})
        if r.status_code >= 300:
            raise GitHubAppError(f"GitHub did not give a token for installation {installation_id} (HTTP {r.status_code})")
        body = r.json()
        expires = calendar.timegm(time.strptime(body["expires_at"], "%Y-%m-%dT%H:%M:%SZ")) if body.get("expires_at") else time.time() + 3000
        self._tokens[installation_id] = (body["token"], expires)
        return body["token"]

    def _installation_get(self, installation_id: int, path: str, **params) -> httpx.Response:
        return self._http().get(f"{API}{path}", params=params or None, headers={"Authorization": f"Bearer {self.installation_token(installation_id)}"})

    def installation_account(self, installation_id: int) -> dict:
        """Who owns the installation (the user or organisation that installed the App)."""
        r = self._http().get(f"{API}/app/installations/{installation_id}", headers={"Authorization": f"Bearer {self.app_jwt()}"})
        if r.status_code >= 300:
            raise GitHubAppError(f"GitHub does not know installation {installation_id} (HTTP {r.status_code})")
        a = r.json().get("account") or {}
        return {"login": a.get("login"), "type": a.get("type")}

    def installation_repos(self, installation_id: int) -> list[dict]:
        out, page = [], 1
        while page <= 10:
            r = self._installation_get(installation_id, "/installation/repositories", per_page=100, page=page)
            if r.status_code >= 300:
                raise GitHubAppError(f"could not list the repositories of installation {installation_id} (HTTP {r.status_code})")
            rows = r.json().get("repositories", [])
            out += [{"id": x["id"], "full_name": x["full_name"], "private": bool(x.get("private")), "default_branch": x.get("default_branch")} for x in rows]
            if len(rows) < 100:
                break
            page += 1
        return out

    def permission(self, installation_id: int, full_name: str, login: str) -> str:
        """What the login may do on the repository: none, read, write or admin."""
        r = self._installation_get(installation_id, f"/repos/{full_name}/collaborators/{login}/permission")
        if r.status_code == 404:
            return "none"
        if r.status_code >= 300:
            raise GitHubAppError(f"could not read the permission of a collaborator (HTTP {r.status_code})")
        return strongest(r.json().get("permission", "none"))

    # ---- a person signs in to GitHub from the system ---------------------------------------------------------------------------------
    def authorize_url(self, state: str, redirect_uri: str, choose_account: bool = False) -> str:
        """Where the person signs in to GitHub. ``choose_account`` makes GitHub ask which account to use even when one is already signed in (for someone who was rejected and must use another)."""
        self._need()
        query = {"client_id": self.config.client_id, "redirect_uri": redirect_uri, "state": state, "allow_signup": "false"}
        if choose_account:
            query["prompt"] = "select_account"
        return f"{WEB}/login/oauth/authorize?" + urlencode(query)

    def exchange_code(self, code: str, redirect_uri: str) -> str:
        self._need()
        r = self._http().post(f"{WEB}/login/oauth/access_token", headers={"Accept": "application/json"},
                              data={"client_id": self.config.client_id, "client_secret": self.config.client_secret, "code": code, "redirect_uri": redirect_uri})
        token = r.json().get("access_token") if r.status_code < 300 else None
        if not token:
            raise GitHubAppError("GitHub did not accept the sign-in code")
        return token

    def user(self, user_token: str) -> dict:
        """The account the token belongs to: GitHub's own numeric id and login. This is what makes a linked account verified."""
        r = self._http().get(f"{API}/user", headers={"Authorization": f"Bearer {user_token}"})
        if r.status_code >= 300:
            raise GitHubAppError("GitHub did not say who signed in")
        u = r.json()
        return {"id": int(u["id"]), "login": str(u["login"]).lower(), "avatar_url": u.get("avatar_url")}

    @property
    def install_url(self) -> str:
        return f"{WEB}/apps/{self.config.slug}/installations/new"


def noreply_emails(github_id: int, login: str) -> list[str]:
    """The addresses GitHub puts on commits made with 'keep my email private': they let commit authors be matched to a linked account with no typing."""
    return [f"{github_id}+{login}@users.noreply.github.com", f"{login}@users.noreply.github.com"]


def sign_state(secret: str, payload: dict[str, Any], ttl: int = 900) -> str:
    return jwt.encode({**payload, "exp": int(time.time()) + ttl}, secret, algorithm="HS256")


def read_state(secret: str, token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError as e:
        raise GitHubAppError("the link has expired or is not valid; start again") from e
