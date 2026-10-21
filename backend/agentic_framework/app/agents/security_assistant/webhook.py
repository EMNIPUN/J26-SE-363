"""GitHub webhook entry path (a plain function, not an HTTP route).

    result = await handle_github_event(headers, raw_body)

Whatever receives the HTTP request later only has to pass the request headers and the *raw* body bytes
to this function. Nothing here opens a port, stores state in a database, or trusts the payload before
its signature has been verified.
"""

import hashlib
import hmac
import json
import logging
import os
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.agents.security_assistant.pipeline import run_pipeline, validate_github_url
from app.agents.security_assistant.schemas import ScanResult

logger = logging.getLogger(__name__)

SECRET_ENV = "SECURITY_ASSISTANT_WEBHOOK_SECRET"
_SHA = re.compile(r"^[0-9a-f]{40}$")

Pipeline = Callable[..., Awaitable[ScanResult]]


@dataclass
class WebhookResult:
    status: str  # processed | ignored | duplicate | rejected | failed
    reason: str
    event: str | None = None
    delivery_id: str | None = None
    scan_type: str | None = None
    repo_url: str | None = None
    commit_sha: str | None = None
    result: ScanResult | None = None


class DedupeStore:
    """Remembers which (commit SHA, scan type) already ran, in memory and bounded.

    A "full" scan covers a "secrets_only" scan of the same SHA, so a push followed by the merged
    pull request for the same commit runs secrets_only first and then full, but never twice.
    Limitation: the memory is lost on restart and is not shared between worker processes (no database
    table was added on purpose).
    """

    def __init__(self, max_entries: int = 10_000):
        self._seen: OrderedDict[str, set[str]] = OrderedDict()
        self._max = max_entries
        self._lock = threading.Lock()

    def claim(self, sha: str, scan_type: str) -> bool:
        """True if this scan should run now (and records it); False if it already ran or is running."""
        with self._lock:
            done = self._seen.setdefault(sha, set())
            if scan_type in done or "full" in done:
                return False
            done.add(scan_type)
            self._seen.move_to_end(sha)
            while len(self._seen) > self._max:
                self._seen.popitem(last=False)
            return True

    def release(self, sha: str, scan_type: str) -> None:
        """Forget a claim, e.g. because the pipeline crashed and GitHub may redeliver."""
        with self._lock:
            self._seen.get(sha, set()).discard(scan_type)


DEFAULT_DEDUPE = DedupeStore()


def verify_signature(secret: str, raw_body: bytes, signature_header: str | None) -> bool:
    """Check the X-Hub-Signature-256 header (`sha256=<hex hmac of the raw body>`) in constant time."""
    if not secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def sign(secret: str, raw_body: bytes) -> str:
    """The header value GitHub would send (used by the replay script and tests)."""
    return "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()


def classify(event: str | None, payload: dict[str, Any]) -> tuple[str, str, str | None]:
    """Decide what to do with a verified event. Returns (action, reason, sha) where action is
    "secrets_only", "full" or "ignore"."""
    if event == "push":
        sha = payload.get("after")
        if payload.get("deleted") or not sha or set(sha) == {"0"}:
            return "ignore", "push deletes the branch or tag, nothing to scan", None
        return "secrets_only", "push: secrets-only scan of the pushed commit", sha
    if event == "pull_request":
        action, pr = payload.get("action"), payload.get("pull_request") or {}
        if action != "closed":
            return "ignore", f"pull_request action '{action}' is not scanned (only merged pull requests)", None
        if pr.get("draft"):
            return "ignore", "draft pull request", None
        if not pr.get("merged"):
            return "ignore", "pull request closed without being merged", None
        sha = pr.get("merge_commit_sha")
        if not sha:
            return "ignore", "merged pull request has no merge_commit_sha", None
        return "full", "merged pull request: full scan of the merge commit", sha
    return "ignore", f"event '{event}' is not scanned", None


async def handle_github_event(
    headers: dict[str, str],
    raw_body: bytes,
    *,
    secret: str | None = None,
    pipeline: Pipeline = run_pipeline,
    dedupe: DedupeStore | None = None,
) -> WebhookResult:
    """Verify, classify, dedupe and run the pipeline for one GitHub webhook delivery.

    `secret` defaults to the SECURITY_ASSISTANT_WEBHOOK_SECRET environment variable; without a secret
    every delivery is rejected. `pipeline` and `dedupe` can be replaced (tests, offline demo).
    """
    h = {k.lower(): v for k, v in headers.items()}
    event, delivery = h.get("x-github-event"), h.get("x-github-delivery")
    store = dedupe if dedupe is not None else DEFAULT_DEDUPE

    def done(status: str, reason: str, **kw) -> WebhookResult:
        logger.info("webhook %s event=%s delivery=%s: %s", status, event, delivery, reason)
        return WebhookResult(status, reason, event=event, delivery_id=delivery, **kw)

    secret = secret if secret is not None else os.environ.get(SECRET_ENV, "")
    if not secret:
        return done("rejected", f"{SECRET_ENV} is not configured, refusing every delivery")
    if not verify_signature(secret, raw_body, h.get("x-hub-signature-256")):
        return done("rejected", "invalid or missing X-Hub-Signature-256")

    try:
        payload = json.loads(raw_body)
        if not isinstance(payload, dict):
            raise ValueError
    except ValueError:
        return done("rejected", "body is not a JSON object")

    action, reason, sha = classify(event, payload)
    if action == "ignore":
        return done("ignored", reason)
    if not _SHA.match(sha or ""):
        return done("rejected", "commit SHA in the payload is not 40 lowercase hex characters")

    repo = payload.get("repository") or {}
    try:
        repo_url = validate_github_url(repo.get("clone_url") or repo.get("html_url") or "")
    except ValueError as exc:
        return done("rejected", str(exc))

    if not store.claim(sha, action):
        return done("duplicate", f"{action} scan of {sha[:12]} already ran or is running",
                    scan_type=action, repo_url=repo_url, commit_sha=sha)
    try:
        result = await pipeline(repo_url, sha, scan_type=action)
    except Exception as exc:  # fetch or pipeline crash: let a redelivery run again
        store.release(sha, action)
        return done("failed", f"{type(exc).__name__}: {exc}"[:300],
                    scan_type=action, repo_url=repo_url, commit_sha=sha)
    return done("processed", reason, scan_type=action, repo_url=repo_url, commit_sha=sha, result=result)
