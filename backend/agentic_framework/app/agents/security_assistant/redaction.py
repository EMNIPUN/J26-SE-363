"""Remove secrets from any text before it is sent to an LLM or written to a report.

Each secret is replaced by a marker that keeps only non-reversible hints the model may need to judge
"live credential or example value": kind, length and whether it looks like a placeholder.
"""

import math
import re
from collections import Counter

_PLACEHOLDER = re.compile(
    r"example|sample|dummy|changeme|change_me|placeholder|your[_-]|xxxx|<.*>|test|fake|redacted|todo|1234|"
    r"secret_here|insert|replace",
    re.I,
)
_NAME = r"[A-Za-z0-9_.\-]*(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|credential)[A-Za-z0-9_.\-]*"

# (kind, regex, group that holds the secret value; 0 = the whole match)
_PATTERNS: list[tuple[str, re.Pattern, int]] = [
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)", re.S), 0),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), 0),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b"), 0),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), 0),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"), 0),
    ("stripe_key", re.compile(r"\b[sr]k_(?:live|test)_[0-9a-zA-Z]{16,}\b"), 0),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b"), 0),
    ("url_password", re.compile(r"\b[a-z][a-z0-9+.\-]*://[^/\s:@]+:([^/\s@]{3,})@"), 1),
    # name = "value" / name: 'value'   (quoted values only: keeps code such as password = request.form[...])
    ("credential", re.compile(rf"(?i)\b{_NAME}\s*[:=]\s*([\"'])([^\"'\n]{{4,}})\1"), 2),
    # name=value / name: value on its own line (.properties, .env, YAML)
    ("credential", re.compile(rf"(?im)^\s*{_NAME}\s*[:=]\s*([^\s\"'#;,(){{}}\[\]$]{{6,}})\s*$"), 1),
    # name=value in the middle of a line (log lines, messages, labels). Only values with a digit or a special
    # character, and not followed by . ( [ , so code like `password = password_hash` or `= request.form` stays.
    ("credential", re.compile(
        rf"(?i)\b{_NAME}\s*[:=]\s*((?=[A-Za-z0-9_@#$%^&*+/=!~\-]*[0-9@#$%^&*+/=!~])[A-Za-z0-9_@#$%^&*+/=!~\-]{{6,}})(?![\w.(\[])"
    ), 1),
    ("high_entropy", re.compile(r"[\"']([A-Za-z0-9+/_=\-]{32,})[\"']"), 1),
]


def _entropy(s: str) -> float:
    counts = Counter(s)
    return -sum(c / len(s) * math.log2(c / len(s)) for c in counts.values())


def _marker(kind: str, value: str) -> str:
    placeholder = "yes" if _PLACEHOLDER.search(value) else "no"
    return f"[REDACTED secret kind={kind} len={len(value)} placeholder_like={placeholder}]"


def redact_text(text: str, known_secrets: tuple[str, ...] = ()) -> str:
    """Replace secrets in `text`. `known_secrets` are literal values that must never appear."""
    if not text:
        return text
    for secret in sorted((s for s in known_secrets if s), key=len, reverse=True):
        text = text.replace(secret, _marker("known", secret))
    for kind, regex, group in _PATTERNS:
        def sub(m: re.Match, kind=kind, group=group):
            value = m.group(group)
            if value.startswith("[REDACTED") or value.startswith("${"):
                return m.group(0)
            if kind == "high_entropy" and _entropy(value) < 3.6:
                return m.group(0)  # long but ordinary text such as a path or identifier
            if group == 0:
                return _marker(kind, value)
            start, end = m.span(group)
            return m.group(0)[: start - m.start()] + _marker(kind, value) + m.group(0)[end - m.start():]

        text = regex.sub(sub, text)
    return text


def find_secret_values(text: str) -> list[str]:
    """The literal secret values in `text`, found with the same patterns and filters as `redact_text`. Governance uses them to check
    that none of them is in a prompt: the check does not trust the replacement it is checking."""
    found: list[str] = []
    for kind, regex, group in _PATTERNS:
        for m in regex.finditer(text or ""):
            value = m.group(group)
            if value.startswith("[REDACTED") or value.startswith("${"):
                continue
            if kind == "high_entropy" and _entropy(value) < 3.6:
                continue
            found.append(value)
    return found
