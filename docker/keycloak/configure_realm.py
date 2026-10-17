#!/usr/bin/env python3
"""Applies SELVIA's email and social-login settings to a running Keycloak realm.

Keycloak only reads realm-export.json when a realm does not exist yet, so changes to it never
reach a realm that is already running. This script does the rest, and is safe to run again:

  * the realm: theme, email as username, brute-force protection, password policy;
  * the mail server Keycloak uses for verification and password-reset emails (KC_SMTP_*);
  * email verification, switched on only when a mail server is configured, so nobody is locked
    out of registering;
  * Google, Microsoft and GitHub sign-in, for each provider whose credentials are set;
  * the web app's addresses (FRONTEND_URLS) and no direct password grants.

Settings come from the environment or from the .env file in the repository root. Nothing secret
is printed. See docker/keycloak/README.md.

    python docker/keycloak/configure_realm.py --dry-run     # show what would change
    python docker/keycloak/configure_realm.py               # apply it
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
KCADM = "/opt/keycloak/bin/kcadm.sh"
SECRET_KEYS = {"clientsecret", "secret", "password"}

PROVIDERS = {
    # alias: (display name, default scope, trust the provider's email, extra config keys from env)
    "google": ("Google", "openid profile email", True),
    "microsoft": ("Microsoft", "openid profile email", False),
    "github": ("GitHub", "user:email", False),
}
# Google states whether an address is verified, so it is trusted. Microsoft's `email` claim can be
# set by a tenant administrator and GitHub's can be changed, so those accounts confirm their
# address by email once; otherwise an attacker could register a provider account with a victim's
# address and take over the victim's SELVIA account.


class ScriptError(Exception):
    pass


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


class Keycloak:
    def __init__(self, container: str, realm: str, dry_run: bool):
        self.container, self.realm, self.dry_run = container, realm, dry_run

    def _run(self, args: list[str], stdin: str | None = None) -> str:
        command = ["docker", "exec", "-i", self.container, KCADM, *args]
        result = subprocess.run(command, input=stdin, capture_output=True, text=True)
        if result.returncode != 0:
            raise ScriptError(f"kcadm {' '.join(args[:2])} failed: {result.stderr.strip()[:300]}")
        return result.stdout

    def login(self) -> None:
        # The admin credentials are already in the container's environment.
        script = (
            f'{KCADM} config credentials --server "http://localhost:8080${{KC_HTTP_RELATIVE_PATH:-}}" '
            '--realm master --user "$KEYCLOAK_ADMIN" --password "$KEYCLOAK_ADMIN_PASSWORD"'
        )
        result = subprocess.run(
            ["docker", "exec", self.container, "sh", "-c", script], capture_output=True, text=True
        )
        if result.returncode != 0:
            raise ScriptError(f"Could not sign in to Keycloak: {result.stderr.strip()[:300]}")

    def get(self, path: str, query: str | None = None):
        args = ["get", path, "-r", self.realm]
        if query:
            args += ["-q", query]
        return json.loads(self._run(args) or "null")

    def put(self, verb: str, path: str, body: dict) -> None:
        self._run([verb, path, "-r", self.realm, "-f", "-"], stdin=json.dumps(body))


def redact(value):
    """For --dry-run output: hide anything that looks like a secret."""
    if isinstance(value, dict):
        return {
            k: "<hidden>" if k.lower() in SECRET_KEYS else redact(v) for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def plan_realm(env: dict[str, str], realm_now: dict) -> tuple[dict, list[str]]:
    notes: list[str] = []
    body: dict = {
        "loginTheme": "mentor",
        "emailTheme": "mentor",
        "registrationAllowed": True,
        "registrationEmailAsUsername": True,
        "loginWithEmailAllowed": True,
        "duplicateEmailsAllowed": False,
        "resetPasswordAllowed": True,
        "bruteForceProtected": True,
        "failureFactor": 5,
        "waitIncrementSeconds": 60,
        "minimumQuickLoginWaitSeconds": 60,
        "maxFailureWaitSeconds": 900,
        "passwordPolicy": "length(10) and notUsername and notEmail",
    }

    host = env.get("KC_SMTP_HOST")
    if host:
        security = env.get("KC_SMTP_SECURITY", "starttls").lower()
        if security not in ("starttls", "ssl", "none"):
            raise ScriptError("KC_SMTP_SECURITY must be starttls, ssl or none")
        sender = env.get("KC_SMTP_FROM")
        if not sender:
            raise ScriptError("KC_SMTP_FROM (the sender address) is required with KC_SMTP_HOST")
        smtp = {
            "host": host,
            "port": env.get("KC_SMTP_PORT", "465" if security == "ssl" else "587"),
            "from": sender,
            "fromDisplayName": env.get("KC_SMTP_FROM_NAME", "SELVIA"),
            "starttls": str(security == "starttls").lower(),
            "ssl": str(security == "ssl").lower(),
            "auth": str(bool(env.get("KC_SMTP_USER"))).lower(),
        }
        if env.get("KC_SMTP_USER"):
            smtp["user"] = env["KC_SMTP_USER"]
            smtp["password"] = env.get("KC_SMTP_PASSWORD", "")
        body["smtpServer"] = smtp

    has_mail = bool(host) or bool((realm_now.get("smtpServer") or {}).get("host"))
    if has_mail:
        body["verifyEmail"] = True
    else:
        notes.append(
            "No mail server (KC_SMTP_HOST): email verification and password reset stay as they "
            "are. Set KC_SMTP_* and run this again to turn verification on."
        )
    return body, notes


def plan_client(env: dict[str, str], client_now: dict) -> tuple[dict, list[str]]:
    notes: list[str] = []
    body: dict = {"directAccessGrantsEnabled": False}
    urls = [u.strip().rstrip("/") for u in env.get("FRONTEND_URLS", "").split(",") if u.strip()]
    if urls:
        body["redirectUris"] = [f"{u}/*" for u in urls]
        body["webOrigins"] = urls
        body["rootUrl"] = urls[0]
        body["baseUrl"] = urls[0]
        attributes = dict(client_now.get("attributes") or {})
        attributes["post.logout.redirect.uris"] = "##".join(f"{u}/*" for u in urls)
        body["attributes"] = attributes
    else:
        broad = [u for u in client_now.get("redirectUris", []) if u in ("*", "https://*", "https://*/*")]
        if broad:
            notes.append(
                f"The client still accepts redirects to {broad}. Set FRONTEND_URLS "
                "(comma separated, e.g. http://localhost:5173,https://app.example.com) to replace them."
            )
    return body, notes


def plan_providers(env: dict[str, str]) -> tuple[dict[str, dict], list[str]]:
    plans: dict[str, dict] = {}
    notes: list[str] = []
    for alias, (display, scope, trust_email) in PROVIDERS.items():
        key = alias.upper()
        client_id, secret = env.get(f"{key}_CLIENT_ID"), env.get(f"{key}_CLIENT_SECRET")
        if not client_id and not secret:
            notes.append(f"{display}: not configured ({key}_CLIENT_ID / {key}_CLIENT_SECRET not set)")
            continue
        if not (client_id and secret):
            raise ScriptError(f"{display}: set both {key}_CLIENT_ID and {key}_CLIENT_SECRET")
        config = {
            "clientId": client_id,
            "clientSecret": secret,
            "defaultScope": scope,
            "syncMode": "IMPORT",
        }
        if alias == "microsoft" and env.get("MICROSOFT_TENANT"):
            config["tenantId"] = env["MICROSOFT_TENANT"]
        plans[alias] = {
            "alias": alias,
            "displayName": display,
            "providerId": alias,
            "enabled": True,
            "trustEmail": trust_email,
            "storeToken": False,
            "firstBrokerLoginFlowAlias": "first broker login",
            "config": config,
        }
    return plans, notes


def callback_url(env: dict[str, str], realm: str, alias: str) -> str:
    base = env.get("KEYCLOAK_HOSTNAME_URL") or f"{env.get('GATEWAY_PUBLIC_URL', 'http://localhost:8000')}/auth"
    return f"{base.rstrip('/')}/realms/{realm}/broker/{alias}/endpoint"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--container", default=None, help="Keycloak container (default: auto-detect)")
    parser.add_argument("--realm", default="mentor")
    parser.add_argument("--dry-run", action="store_true", help="show the changes, apply nothing")
    args = parser.parse_args()

    env = {**load_env_file(REPO_ROOT / ".env"), **os.environ}
    container = args.container or env.get("KEYCLOAK_CONTAINER")
    kc = Keycloak(container or "", args.realm, args.dry_run)

    if not container:
        names = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True
        ).stdout.split()
        found = [n for n in names if n.endswith("keycloak")]
        if len(found) != 1:
            raise ScriptError(f"Name the Keycloak container with --container (found: {found or 'none'})")
        kc.container = found[0]

    print(f"Keycloak container: {kc.container}, realm: {args.realm}{' (dry run)' if args.dry_run else ''}")
    kc.login()
    realm_now = kc.get(f"realms/{args.realm}")
    clients = kc.get("clients", "clientId=mentor-frontend") or []
    if not clients:
        raise ScriptError("The mentor-frontend client was not found in this realm")
    client_now = clients[0]

    realm_body, notes = plan_realm(env, realm_now)
    client_body, client_notes = plan_client(env, client_now)
    providers, provider_notes = plan_providers(env)
    notes += client_notes + provider_notes

    steps: list[tuple[str, str, str, dict]] = [("realm settings", "update", f"realms/{args.realm}", realm_body)]
    steps.append(("web app client", "update", f"clients/{client_now['id']}", client_body))
    existing = {i["alias"] for i in (kc.get("identity-provider/instances") or [])}
    for alias, body in providers.items():
        if alias in existing:
            steps.append((f"{body['displayName']} sign-in (update)", "update", f"identity-provider/instances/{alias}", body))
        else:
            steps.append((f"{body['displayName']} sign-in (create)", "create", "identity-provider/instances", body))

    for label, verb, path, body in steps:
        if args.dry_run:
            print(f"- {label}: {json.dumps(redact(body), indent=2)}")
        else:
            kc.put(verb, path, body)
            print(f"- {label}: done")

    for alias in providers:
        print(f"{PROVIDERS[alias][0]} redirect URI to register: {callback_url(env, args.realm, alias)}")
    for note in notes:
        print(f"note: {note}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ScriptError as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
