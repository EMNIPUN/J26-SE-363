"""What the Groq keys have used, and how much of each limit is left.

Groq has no call that answers "how much of my daily allowance is left", so every call the agent makes is written to a small
SQLite ledger (``logs/groq_usage.sqlite``, git-ignored), and the usage endpoint adds the ledger up against the limits of the
account (the Limits page of the Groq console; ``MODEL_LIMITS`` below). The ledger is a file so the worker, which makes the
calls, and the HTTP server, which reports them, can be separate processes.

A key is never stored: only a short fingerprint of it and its position in ``GROQ_API_KEYS`` ("key 1" is the first one).
Writing to the ledger can never fail a call to the model: every error here is swallowed.
"""

import hashlib
import json
import os
import re
import sqlite3
import time
from pathlib import Path

LEDGER = Path(os.environ.get("GROQ_USAGE_DB") or Path(__file__).resolve().parents[2] / "logs" / "groq_usage.sqlite")
SETTINGS_FILE = Path(__file__).resolve().parents[1] / "agents" / "performance_assessment" / ".env"
DAY = 24 * 3600

# The account's base limits per key (rpm, rpd = requests per minute / day; tpm, tpd = tokens per minute / day), from the Groq console.
MODEL_LIMITS = {
    "allam-2-7b": {"rpm": 30, "rpd": 7000, "tpm": 6000, "tpd": 500_000},
    "meta-llama/llama-prompt-guard-2-22m": {"rpm": 30, "rpd": 14_400, "tpm": 15_000, "tpd": 500_000},
    "meta-llama/llama-prompt-guard-2-86m": {"rpm": 30, "rpd": 14_400, "tpm": 15_000, "tpd": 500_000},
    "openai/gpt-oss-120b": {"rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200_000},
    "openai/gpt-oss-20b": {"rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200_000},
    "openai/gpt-oss-safeguard-20b": {"rpm": 3, "rpd": 1000, "tpm": 2000, "tpd": 200_000},
    "qwen/qwen3.8-27b": {"rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200_000},
}
DEFAULT_AVG_TOKENS = 4000  # a guess for how big one call is, used only until there are calls to measure

_SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
    ts REAL NOT NULL, key_fp TEXT NOT NULL, key_idx INTEGER NOT NULL, model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0, completion_tokens INTEGER NOT NULL DEFAULT 0,
    ok INTEGER NOT NULL, status INTEGER, error_kind TEXT NOT NULL DEFAULT '', retry_after REAL,
    rem_req INTEGER, rem_tok INTEGER, lim_req INTEGER, lim_tok INTEGER, source TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS calls_ts ON calls (ts);
"""


# --- keys -------------------------------------------------------------------------------------------------------------

def fingerprint(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()[:8]


def configured_keys() -> list[str]:
    """The keys in the order the agent uses them: the environment first, then the GROQ_API_KEYS line of the settings file."""
    raw = os.environ.get("GROQ_API_KEYS") or os.environ.get("GROQ_API_KEY", "")
    if not raw:
        try:
            for line in SETTINGS_FILE.read_text(encoding="utf-8").splitlines():
                m = re.match(r"^\s*GROQ_API_KEYS?\s*=\s*(.*?)\s*$", line)
                if m:
                    raw = m.group(1).strip().strip("\"'")
                    break
        except OSError:
            pass
    return [k.strip() for k in raw.split(",") if k.strip()]


def settings_models() -> list[str]:
    """The models the agent is set to use (primary, then fallback), whatever their names are."""
    values = {"GROQ_MODEL": os.environ.get("GROQ_MODEL"), "GROQ_FALLBACK_MODEL": os.environ.get("GROQ_FALLBACK_MODEL")}
    try:
        for line in SETTINGS_FILE.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*(GROQ_MODEL|GROQ_FALLBACK_MODEL)\s*=\s*(.*?)\s*$", line)
            if m and not values[m.group(1)]:
                values[m.group(1)] = m.group(2).strip().strip("\"'")
    except OSError:
        pass
    return [v for v in (values["GROQ_MODEL"], values["GROQ_FALLBACK_MODEL"]) if v]


# --- writing ----------------------------------------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(LEDGER, timeout=5)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(_SCHEMA)
    return db


def to_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _wait_seconds(text: str) -> float | None:
    """Seconds in a 'try again in 1h2m3.5s' hint, or in a header such as '12m3s' or '850ms'."""
    found = re.findall(r"(\d+(?:\.\d+)?)(ms|h|m|s)", text or "")
    if not found:
        return None
    return sum(float(v) * {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}[u] for v, u in found)


def record(secret: str, model: str, *, ok: bool, status: int | None = None, usage: dict | None = None, headers=None,
           error_kind: str = "", error_text: str = "", source: str = "") -> None:
    """One call to Groq. ``headers`` are the response headers (their rate-limit fields show what the service says is left)."""
    try:
        keys = configured_keys()
        fp = fingerprint(secret)
        idx = next((i + 1 for i, k in enumerate(keys) if k == secret), 0)
        get = (lambda name: headers.get(name)) if headers is not None else (lambda name: None)
        usage = usage or {}
        retry = None
        header = get("retry-after")
        if header:
            try:
                retry = float(header)  # Groq sends whole seconds
            except ValueError:
                retry = _wait_seconds(str(header))
        if retry is None and error_text:
            m = re.search(r"try again in\s+((?:\d+(?:\.\d+)?(?:ms|h|m|s))+)", error_text)
            retry = _wait_seconds(m.group(1)) if m else None
        with _connect() as db:
            db.execute(
                "INSERT INTO calls (ts, key_fp, key_idx, model, prompt_tokens, completion_tokens, ok, status, error_kind, retry_after, rem_req, rem_tok, lim_req, lim_tok, source)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (time.time(), fp, idx, model, int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0), 1 if ok else 0, status, error_kind, retry,
                 to_int(get("x-ratelimit-remaining-requests")), to_int(get("x-ratelimit-remaining-tokens")), to_int(get("x-ratelimit-limit-requests")), to_int(get("x-ratelimit-limit-tokens")), source),
            )
        db.close()
    except Exception:  # the ledger must never break a call to the model
        pass


# --- reading ----------------------------------------------------------------------------------------------------------

def _rows(since: float) -> list[dict]:
    try:
        db = _connect()
        db.row_factory = sqlite3.Row
        rows = [dict(r) for r in db.execute("SELECT * FROM calls WHERE ts >= ? ORDER BY ts", (since,))]
        db.close()
        return rows
    except Exception:
        return []


def _level(used_fraction: float, blocked: bool) -> str:
    if blocked or used_fraction >= 1:
        return "exhausted"
    if used_fraction >= 0.9:
        return "critical"
    if used_fraction >= 0.7:
        return "warning"
    return "ok"


WORST = {"ok": 0, "warning": 1, "critical": 2, "exhausted": 3}


def _eta(remaining: int, per_minute: float) -> dict:
    """When a budget of ``remaining`` runs out at ``per_minute``, as minutes and a plain sentence."""
    if per_minute <= 0:
        return {"minutes": None, "text": "not being used right now"}
    minutes = remaining / per_minute
    if minutes >= 24 * 60:
        return {"minutes": round(minutes), "text": "lasts more than a day at this pace"}
    h, m = divmod(int(minutes), 60)
    return {"minutes": round(minutes), "text": f"runs out in about {h}h {m}m at this pace" if h else f"runs out in about {m} min at this pace"}


def _cell(rows: list[dict], model: str, limits: dict | None, now: float) -> dict:
    """One key on one model: used, left and the pace, from that key's calls on that model in the last 24 hours."""
    ok = [r for r in rows if r["ok"]]
    tokens = lambda rs: sum(r["prompt_tokens"] + r["completion_tokens"] for r in rs)  # noqa: E731
    day_tokens, day_requests = tokens(ok), len(ok)
    minute = [r for r in ok if now - r["ts"] <= 60]
    half_hour = [r for r in ok if now - r["ts"] <= 1800]
    pace = tokens(half_hour) / 30.0
    quota = [r for r in rows if not r["ok"] and r["error_kind"] == "quota" and r["retry_after"] and r["ts"] + r["retry_after"] > now]
    blocked_for = max((r["ts"] + r["retry_after"] - now for r in quota), default=0)
    errors = {}
    for r in rows:
        if not r["ok"]:
            errors[r["error_kind"] or "error"] = errors.get(r["error_kind"] or "error", 0) + 1
    cell = {
        "tokens_24h": day_tokens, "requests_24h": day_requests, "tokens_last_minute": tokens(minute), "requests_last_minute": len(minute),
        "tokens_per_minute_now": round(pace, 1), "errors_24h": errors, "last_call": max((r["ts"] for r in rows), default=None),
        "blocked_for_seconds": round(blocked_for) if blocked_for > 0 else 0,
    }
    seen = next((r for r in reversed(rows) if r["rem_req"] is not None or r["rem_tok"] is not None), None)
    if seen:
        cell["reported_by_groq"] = {"requests_left_today": seen["rem_req"], "tokens_left_this_minute": seen["rem_tok"], "seen_seconds_ago": round(now - seen["ts"])}
    if not limits:
        return {**cell, "limits": None, "level": "unknown", "note": "this model is not in MODEL_LIMITS, so no limit is known"}
    tokens_left = max(0, limits["tpd"] - day_tokens)
    requests_left = max(0, limits["rpd"] - day_requests)
    fraction = max(day_tokens / limits["tpd"], day_requests / limits["rpd"])
    return {
        **cell, "limits": limits, "tokens_left_today": tokens_left, "requests_left_today": requests_left,
        "percent_used": round(100 * fraction, 1), "level": _level(fraction, blocked_for > 0),
        "minute_pressure_percent": round(100 * max(tokens(minute) / limits["tpm"], len(minute) / limits["rpm"]), 1),
        "runs_out": _eta(tokens_left, pace),
    }


def snapshot(now: float | None = None) -> dict:
    """Everything the usage endpoint shows: each key, each model across all keys, and a verdict for the next few hours."""
    now = now or time.time()
    keys = configured_keys()
    rows = _rows(now - DAY)
    by_fp = {fingerprint(k): i + 1 for i, k in enumerate(keys)}
    for r in rows:  # a call made with a key that has since been removed from the list keeps its own label
        r["key_idx"] = by_fp.get(r["key_fp"], r["key_idx"] or 0)
    labels = {i + 1: fingerprint(k) for i, k in enumerate(keys)}
    for r in rows:
        labels.setdefault(r["key_idx"], r["key_fp"])
    used_models = {r["model"] for r in rows}
    models = list(dict.fromkeys([*settings_models(), *sorted(used_models)]))

    per_key = []
    for idx in sorted(labels):
        mine = [r for r in rows if r["key_idx"] == idx]
        entry = {"key": idx, "name": f"Key {idx}", "fingerprint": labels[idx], "configured": idx <= len(keys), "models": {}}
        for model in models:
            if any(r["model"] == model for r in mine) or model in settings_models():
                entry["models"][model] = _cell([r for r in mine if r["model"] == model], model, MODEL_LIMITS.get(model), now)
        entry["level"] = max((c["level"] for c in entry["models"].values() if c["level"] in WORST), key=WORST.get, default="ok")
        entry["total_tokens_24h"] = sum(c["tokens_24h"] for c in entry["models"].values())
        entry["total_requests_24h"] = sum(c["requests_24h"] for c in entry["models"].values())
        per_key.append(entry)

    combined = {}
    for model in models:
        limits = MODEL_LIMITS.get(model)
        cells = [(e["key"], e["models"][model]) for e in per_key if model in e["models"] and e["configured"]]
        mine = [r for r in rows if r["model"] == model]
        ok = [r for r in mine if r["ok"]]
        calls = ok[-50:]
        avg = round(sum(r["prompt_tokens"] + r["completion_tokens"] for r in calls) / len(calls)) if calls else DEFAULT_AVG_TOKENS
        entry = {"keys": len(cells), "tokens_24h": sum(c["tokens_24h"] for _, c in cells), "requests_24h": sum(c["requests_24h"] for _, c in cells),
                 "average_tokens_per_call": avg, "average_is_measured": bool(calls), "tokens_per_minute_now": round(sum(c["tokens_per_minute_now"] for _, c in cells), 1),
                 "errors_24h": {}}
        for r in mine:
            if not r["ok"]:
                entry["errors_24h"][r["error_kind"] or "error"] = entry["errors_24h"].get(r["error_kind"] or "error", 0) + 1
        if limits and cells:
            live = [c for _, c in cells if c["level"] != "exhausted"]
            budget = {"tokens": limits["tpd"] * len(cells), "requests": limits["rpd"] * len(cells)}
            tokens_left = sum(c["tokens_left_today"] for _, c in cells if c["level"] != "exhausted")
            requests_left = sum(c["requests_left_today"] for _, c in cells if c["level"] != "exhausted")
            fraction = 1 - tokens_left / budget["tokens"] if budget["tokens"] else 1
            entry.update({
                "limits_per_key": limits, "daily_budget": budget, "tokens_left_today": tokens_left, "requests_left_today": requests_left,
                "percent_used": round(100 * max(entry["tokens_24h"] / budget["tokens"], entry["requests_24h"] / budget["requests"]), 1),
                "keys_usable": len(live), "keys_exhausted": len(cells) - len(live),
                "calls_left_estimate": min(tokens_left // max(avg, 1), requests_left),
                "runs_out": _eta(tokens_left, entry["tokens_per_minute_now"]),
                "level": "exhausted" if not live else _level(fraction, False),
                "largest_single_request_tokens": limits["tpm"],
            })
        else:
            entry.update({"limits_per_key": limits, "level": "unknown"})
        combined[model] = entry

    primary = [m for m in settings_models() if combined.get(m, {}).get("level") in WORST]
    worst = max((combined[m]["level"] for m in primary), key=WORST.get, default="ok")
    left = {m: combined[m].get("calls_left_estimate") for m in primary}
    messages = []
    for m in primary:
        c = combined[m]
        messages.append(f"{m}: {c['keys_usable']} of {c['keys']} keys usable, {c['tokens_left_today']:,} of {c['daily_budget']['tokens']:,} tokens left today "
                        f"(about {c['calls_left_estimate']} more calls at {c['average_tokens_per_call']:,} tokens each); {c['runs_out']['text']}.")
    if not rows:
        messages.append("No Groq calls have been recorded yet, so everything shows as unused. Calls made before the ledger existed are not counted: run /usage/groq/probe to read the live figures.")
    return {
        "generated_at": now, "window": "the last 24 hours, rolling",
        "verdict": {"level": worst, "ready_for_demo": worst in ("ok", "warning") and bool(keys), "calls_left_estimate": left, "summary": messages},
        "keys_configured": len(keys), "models": combined, "keys": per_key,
        "notes": ["Daily figures add up what this agent sent in the last 24 hours; Groq's own daily window may differ a little, and usage from other tools or people on the same keys is not counted.",
                  "'reported_by_groq' is what Groq said in its response headers after the key's latest call; /usage/groq/probe refreshes it."],
    }
