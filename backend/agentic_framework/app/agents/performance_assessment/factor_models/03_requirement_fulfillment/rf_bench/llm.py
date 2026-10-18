"""Language-model access for every experiment: Groq only (plan.md, section 13), plus a scripted model for tests.

Keys are read from the environment (``GROQ_API_KEYS``, comma separated) and are never printed, logged or written to a result; a key is
identified by its index only. The account limits are the binding constraint (8,000 tokens per minute and 1,000 requests per day per key
on the account that was checked): every call is paced against them, a request larger than the per-minute limit is sent anyway and the
refusal is recorded as a ``too_large`` failure of the arm that made it, not hidden and not retried.
"""

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .schema import est_tokens

URL = "https://api.groq.com/openai/v1/chat/completions"
USAGE_FILE = Path(__file__).resolve().parents[1] / ".runs" / "groq_usage.json"


@dataclass
class Reply:
    text: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency: float = 0.0
    model: str = ""
    error: str = ""             # empty when the call succeeded
    error_kind: str = ""        # too_large | rate_limited | quota | server | network | no_key
    attempts: int = 0
    key: int = -1
    meta: dict = field(default_factory=dict)

    @property
    def ok(self):
        return not self.error


class LLM:
    """Interface: ``chat(messages, ...) -> Reply``. ``messages`` are OpenAI-style dicts."""

    model = "none"

    def chat(self, messages, *, max_tokens=1200, temperature=0.0, json_mode=True, tag="", seed=None):
        raise NotImplementedError


class ScriptedLLM(LLM):
    """A model that answers from a function; used to test whole pipelines without a network or a key."""

    def __init__(self, responder, model="scripted", limit_tokens=None):
        self.responder, self.model, self.limit, self.n = responder, model, limit_tokens, 0

    def chat(self, messages, *, max_tokens=1200, temperature=0.0, json_mode=True, tag="", seed=None):
        self.n += 1
        prompt = sum(est_tokens(m["content"]) for m in messages)
        if self.limit and prompt > self.limit:
            return Reply(error=f"request too large ({prompt} tokens)", error_kind="too_large", prompt_tokens=prompt, model=self.model, attempts=1)
        text = self.responder(messages, tag)
        return Reply(text=text, prompt_tokens=prompt, completion_tokens=est_tokens(text), model=self.model, attempts=1, latency=0.0)


# --- Groq ---------------------------------------------------------------------------------------------------------------

class _Key:
    def __init__(self, index, secret):
        self.index, self.secret = index, secret
        self.window = deque()      # (time, tokens) of the last 60 seconds
        self.lock = threading.Lock()
        self.dead_until = 0.0

    def used(self, now):
        while self.window and now - self.window[0][0] > 60:
            self.window.popleft()
        return sum(t for _, t in self.window)


class GroqPool(LLM):
    def __init__(self, model=None, fallback=None, tpm=8000, rpd=1000, effort="low", keys=None, timeout=120):
        raw = keys if keys is not None else [k.strip() for k in os.environ.get("GROQ_API_KEYS", "").split(",") if k.strip()]
        if not raw:
            raise RuntimeError("GROQ_API_KEYS is not set in the environment")
        self.keys = [_Key(i, k) for i, k in enumerate(raw)]
        self.model = model or os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
        self.fallback = fallback or os.environ.get("GROQ_FALLBACK_MODEL", "")
        self.tpm, self.rpd, self.effort, self.timeout = tpm, rpd, effort, timeout
        self.lock = threading.Lock()
        self.daily = self._load_daily()

    # daily request counters are kept by key index, never by key value
    def _load_daily(self):
        try:
            d = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
            return d if d.get("date") == str(date.today()) else {"date": str(date.today()), "requests": {}, "exhausted": []}
        except Exception:
            return {"date": str(date.today()), "requests": {}, "exhausted": []}

    def _save_daily(self):
        try:
            USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
            USAGE_FILE.write_text(json.dumps(self.daily), encoding="utf-8")
        except Exception:
            pass

    def _wait(self, k, need, now):
        """Seconds until key ``k`` can take ``need`` more tokens inside the per-minute limit."""
        if need > self.tpm:
            return 0.0  # cannot fit at all: sent anyway, the server's refusal is the finding
        live = sorted((ts, tok) for ts, tok in k.window if now - ts <= 60)
        used = sum(tok for _, tok in live)
        if used + need <= self.tpm:
            return 0.0
        for ts, tok in live:
            used -= tok
            if used + need <= self.tpm:
                return max(0.0, ts + 60 - now)
        return 60.0

    def _pick(self, need):
        """The key that can take ``need`` tokens soonest. Reserves the tokens. Returns (key, wait_seconds)."""
        with self.lock:
            now = time.time()
            best, best_wait = None, 1e9
            for k in self.keys:
                if k.index in self.daily["exhausted"] or self.daily["requests"].get(str(k.index), 0) >= self.rpd or k.dead_until > now:
                    continue
                wait = self._wait(k, need, now)
                if wait < best_wait:
                    best, best_wait = k, wait
            if best is None:
                return None, 0.0
            best.window.append((now + best_wait, min(need, self.tpm)))
            self.daily["requests"][str(best.index)] = self.daily["requests"].get(str(best.index), 0) + 1
            return best, best_wait

    def chat(self, messages, *, max_tokens=1200, temperature=0.0, json_mode=True, tag="", seed=None):
        raise NotImplementedError


class ScriptedLLM(LLM):
    """A model that answers from a function; used to test whole pipelines without a network or a key."""

    def __init__(self, responder, model="scripted", limit_tokens=None):
        self.responder, self.model, self.limit, self.n = responder, model, limit_tokens, 0

    def chat(self, messages, *, max_tokens=1200, temperature=0.0, json_mode=True, tag="", seed=None):
        self.n += 1
        prompt = sum(est_tokens(m["content"]) for m in messages)
        if self.limit and prompt > self.limit:
            return Reply(error=f"request too large ({prompt} tokens)", error_kind="too_large", prompt_tokens=prompt, model=self.model, attempts=1)
        text = self.responder(messages, tag)
        return Reply(text=text, prompt_tokens=prompt, completion_tokens=est_tokens(text), model=self.model, attempts=1, latency=0.0)


# --- Groq ---------------------------------------------------------------------------------------------------------------

class _Key:
    def __init__(self, index, secret):
        self.index, self.secret = index, secret
        self.window = deque()      # (time, tokens) of the last 60 seconds
        self.lock = threading.Lock()
        self.dead_until = 0.0

    def used(self, now):
        while self.window and now - self.window[0][0] > 60:
            self.window.popleft()
        return sum(t for _, t in self.window)


class GroqPool(LLM):
    def __init__(self, model=None, fallback=None, tpm=8000, rpd=1000, effort="low", keys=None, timeout=120):
        raw = keys if keys is not None else [k.strip() for k in os.environ.get("GROQ_API_KEYS", "").split(",") if k.strip()]
        if not raw:
            raise RuntimeError("GROQ_API_KEYS is not set in the environment")
        self.keys = [_Key(i, k) for i, k in enumerate(raw)]
        self.model = model or os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
        self.fallback = fallback or os.environ.get("GROQ_FALLBACK_MODEL", "")
        self.tpm, self.rpd, self.effort, self.timeout = tpm, rpd, effort, timeout
        self.lock = threading.Lock()
        self.daily = self._load_daily()

    # daily request counters are kept by key index, never by key value
    def _load_daily(self):
        try:
            d = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
            return d if d.get("date") == str(date.today()) else {"date": str(date.today()), "requests": {}, "exhausted": []}
        except Exception:
            return {"date": str(date.today()), "requests": {}, "exhausted": []}

    def _save_daily(self):
        try:
            USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
            USAGE_FILE.write_text(json.dumps(self.daily), encoding="utf-8")
        except Exception:
            pass

    def _pick(self, need):
        """The key that can take ``need`` tokens soonest. Reserves the tokens. Returns (key, wait_seconds)."""
        with self.lock:
            now = time.time()
            best, best_wait = None, 1e9
            for k in self.keys:
                if k.index in self.daily["exhausted"] or self.daily["requests"].get(str(k.index), 0) >= self.rpd or k.dead_until > now:
                    continue
                used = k.used(now)
                if used + need <= self.tpm or need > self.tpm:
                    wait = 0.0 if (used + need <= self.tpm) else max(0.0, 60 - (now - k.window[0][0])) if k.window else 0.0
                else:
                    cum, wait = used, 0.0
                    for t, tok in k.window:
                        cum -= tok
                        wait = 60 - (now - t)
                        if cum + need <= self.tpm:
                            break
                if wait < best_wait:
                    best, best_wait = k, wait
            if best is None:
                return None, 0.0
            best.window.append((now + best_wait, min(need, self.tpm)))
            self.daily["requests"][str(best.index)] = self.daily["requests"].get(str(best.index), 0) + 1
            return best, best_wait

    def chat(self, messages, *, max_tokens=1200, temperature=0.0, json_mode=True, tag="", seed=None):
        need = sum(est_tokens(m["content"]) for m in messages) + max_tokens
        body = {"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if seed is not None:
            body["seed"] = int(seed)
        if "gpt-oss" in self.model:
            body["reasoning_effort"] = self.effort
        t0, attempts = time.time(), 0
        last = Reply(model=self.model, error="no key available", error_kind="no_key")
        while attempts < 6:
            key, wait = self._pick(need)
            if key is None:
                last.error, last.error_kind = "every key is exhausted for today", "quota"
                break
            if wait > 0:
                time.sleep(wait)
            attempts += 1
            reply = self._call(key, body)
            reply.attempts, reply.key = attempts, key.index
            if reply.ok or reply.error_kind in ("too_large", "bad_request"):
                reply.latency = time.time() - t0
                self._save_daily()
                return reply
            last = reply
            if reply.error_kind == "quota":
                with self.lock:
                    self.daily["exhausted"].append(key.index)
                continue
            time.sleep(min(float(reply.meta.get("retry_after", 5)), 65))
        last.latency, last.attempts = time.time() - t0, attempts
        self._save_daily()
        return last

    def _call(self, key, body):
        req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {key.secret}", "Content-Type": "application/json", "User-Agent": "rf-bench/1"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
                u = data.get("usage", {})
                return Reply(text=data["choices"][0]["message"].get("content") or "", prompt_tokens=u.get("prompt_tokens", 0),
                             completion_tokens=u.get("completion_tokens", 0), model=data.get("model", body["model"]))
        except urllib.error.HTTPError as e:
            text = ""
            try:
                text = e.read().decode()[:600]
            except Exception:
                pass
            msg = re.sub(r"gsk_[A-Za-z0-9]+", "gsk_***", text)
            retry = re.search(r"try again in ([\d.]+)(ms|s|m)", msg)
            after = float(retry.group(1)) / (1000 if retry.group(2) == "ms" else 1) * (60 if retry.group(2) == "m" else 1) + 0.5 if retry else 8
            low = msg.lower()
            if e.code == 413 or "request too large" in low or "request_too_large" in low:
                return Reply(model=body["model"], error=f"HTTP {e.code}: {msg[:300]}", error_kind="too_large")
            if e.code == 429 and ("per day" in low or "tpd" in low or "rpd" in low):
                return Reply(model=body["model"], error=f"HTTP 429: {msg[:200]}", error_kind="quota")
            if e.code == 429:
                return Reply(model=body["model"], error=f"HTTP 429: {msg[:200]}", error_kind="rate_limited", meta={"retry_after": after})
            if e.code == 400:
                return Reply(model=body["model"], error=f"HTTP 400: {msg[:300]}", error_kind="bad_request")
            return Reply(model=body["model"], error=f"HTTP {e.code}: {msg[:200]}", error_kind="server", meta={"retry_after": 5})
        except Exception as e:  # network, timeout, malformed body
            return Reply(model=body["model"], error=f"{type(e).__name__}: {str(e)[:160]}", error_kind="network", meta={"retry_after": 5})


def parse_json(text):
    """The first JSON object in a model reply, or None."""
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None
