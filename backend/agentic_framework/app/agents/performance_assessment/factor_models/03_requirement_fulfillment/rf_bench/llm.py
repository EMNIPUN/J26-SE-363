"""Language-model access for every experiment: Groq only (plan.md, section 13), plus a scripted model for tests.

Keys are read from the environment (``ASSESSMENT_GROQ_API_KEYS``, comma separated) and are never printed, logged or written to a result; a key is
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

try:
    from app.core.groq_usage import record as record_usage  # what each key has used, for the usage endpoint of the service
except ImportError:  # the experiments run on their own, outside the service: nothing is recorded
    def record_usage(*args, **kwargs):
        return None

URL = "https://api.groq.com/openai/v1/chat/completions"
PRECHECK_FACTOR = 1.3  # estimated prompt tokens above this many times the per-minute limit are certain to be refused (the estimate is within about +-20%)
USAGE_FILE = Path(__file__).resolve().parents[1] / ".runs" / "groq_usage.json"


@dataclass
class Reply:
    text: str = ""
    reasoning: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency: float = 0.0
    model: str = ""
    error: str = ""             # empty when the call succeeded
    error_kind: str = ""        # too_large | rate_limited | quota | server | network | no_key
    attempts: int = 0
    key: int = -1
    meta: dict = field(default_factory=dict)
    tool_calls: list = field(default_factory=list)   # [{"name": str, "arguments": dict}] when the model called a function

    @property
    def ok(self):
        return not self.error


class LLM:
    """Interface: ``chat(messages, ...) -> Reply``. ``messages`` are OpenAI-style dicts."""

    model = "none"

    def chat(self, messages, *, max_tokens=1200, temperature=0.0, json_mode=True, tag="", seed=None, model=None, tools=None):
        raise NotImplementedError


class ScriptedLLM(LLM):
    """A model that answers from a function; used to test whole pipelines without a network or a key."""

    def __init__(self, responder, model="scripted", limit_tokens=None):
        self.responder, self.model, self.limit, self.n = responder, model, limit_tokens, 0

    def chat(self, messages, *, max_tokens=1200, temperature=0.0, json_mode=True, tag="", seed=None, model=None, tools=None):
        self.n += 1
        prompt = sum(est_tokens(m["content"]) for m in messages)
        if self.limit and prompt > self.limit:
            return Reply(error=f"request too large ({prompt} tokens)", error_kind="too_large", prompt_tokens=prompt, model=self.model, attempts=1)
        text = self.responder(messages, tag)
        reasoning = ""
        if isinstance(text, str) and "<think>" in text:
            m = re.search(r"<think>(.*?)</think>", text, flags=re.DOTALL)
            if m:
                reasoning = m.group(1).strip()
                text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        return Reply(text=text, reasoning=reasoning, prompt_tokens=prompt, completion_tokens=est_tokens(text), model=self.model, attempts=1, latency=0.0)


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


def load_env_file(path):
    """Read only the ASSESSMENT_GROQ_* settings from a dotenv-style file the owner pointed to (``RF_ENV_FILE``). Nothing else is read or kept."""
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*(ASSESSMENT_GROQ_[A-Z_]+)\s*=\s*(.*?)\s*$", line)
        if m and m.group(1) not in os.environ:
            os.environ[m.group(1)] = m.group(2).strip().strip("\"'")


class GroqPool(LLM):
    def __init__(self, model=None, fallback=None, tpm=8000, rpd=1000, effort="low", keys=None, timeout=120):
        if keys is None and not os.environ.get("ASSESSMENT_GROQ_API_KEYS") and os.environ.get("RF_ENV_FILE"):
            load_env_file(os.environ["RF_ENV_FILE"])
        raw = keys if keys is not None else [k.strip() for k in os.environ.get("ASSESSMENT_GROQ_API_KEYS", "").split(",") if k.strip()]
        if not raw:
            raise RuntimeError("ASSESSMENT_GROQ_API_KEYS is not set in the environment")
        self.keys = [_Key(i, k) for i, k in enumerate(raw)]
        self.model = model or os.environ.get("ASSESSMENT_GROQ_MODEL", "openai/gpt-oss-120b")
        self.fallback = fallback or os.environ.get("ASSESSMENT_GROQ_FALLBACK_MODEL", "")
        self.tpm, self.rpd, self.effort, self.timeout = tpm, rpd, effort, timeout
        self.wait_quota = os.environ.get("RF_WAIT") == "1"  # wait for the daily token limit to refill instead of returning a quota error
        self.lock = threading.Lock()
        self.daily = self._load_daily()

    # daily request counters are kept by key index, never by key value
    def _load_daily(self):
        try:
            d = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
            # the request counts are kept for the day; "exhausted" is not: a key is tried again in every new process, and a real limit is found again at once
            return {**d, "exhausted": []} if d.get("date") == str(date.today()) else {"date": str(date.today()), "requests": {}, "exhausted": []}
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

    def chat(self, messages, *, max_tokens=1200, temperature=0.0, json_mode=True, tag="", seed=None, model=None, tools=None):
        """``tools``: OpenAI-style function definitions; the model must call one of them (``Reply.tool_calls``). ``model`` overrides the pool's model for this call (the critic uses another family); limits are shared across models."""
        prompt_est = sum(est_tokens(m["content"]) for m in messages)
        need = prompt_est + max_tokens
        if prompt_est > PRECHECK_FACTOR * self.tpm:
            # The service refuses a request above the per-minute limit (HTTP 413), but when the daily bucket is low it answers such a request with a
            # daily-limit 429 first, and waiting hours to be told "too large" helps nobody. A request this far above the limit is not sent.
            return Reply(error=f"not sent: about {prompt_est} tokens against the account's {self.tpm} tokens per minute; the service refuses such requests",
                         error_kind="too_large", model=self.model, attempts=0, meta={"client_precheck": True})
        use = model or self.model
        body = {"model": use, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "required"
        elif json_mode:
            body["response_format"] = {"type": "json_object"}
        if seed is not None:
            body["seed"] = int(seed)
        if "gpt-oss" in use:
            body["reasoning_effort"] = self.effort
        if "qwen" in use:
            body["reasoning_format"] = "parsed"  # expose model reasoning for live trace
        t0, attempts = time.time(), 0
        last = Reply(model=self.model, error="no key available", error_kind="no_key")
        while attempts < 6:
            key, wait = self._pick(need)
            if key is None:
                if self.wait_quota:  # every key is at its daily limit: the limit refills continuously, so wait for the soonest key
                    with self.lock:
                        soonest = min((k.dead_until for k in self.keys), default=0) - time.time()
                    time.sleep(min(max(soonest, 1.0), 1800.0))
                    continue
                last.error, last.error_kind = "every key is at its daily token limit", "quota"
                break
            if wait > 0:
                time.sleep(wait)
            attempts += 1
            reply = self._call(key, body)
            reply.attempts, reply.key = attempts, key.index
            if reply.error_kind == "bad_request" and "reasoning" in reply.error.lower() and ("reasoning_format" in body or "reasoning_effort" in body):
                body.pop("reasoning_format", None)  # this model does not take the option: send without it, once
                body.pop("reasoning_effort", None)
                continue
            if reply.ok or reply.error_kind in ("too_large", "bad_request"):
                reply.latency = time.time() - t0
                self._save_daily()
                return reply
            last = reply
            if reply.error_kind == "quota":
                with self.lock:  # this key is skipped until the refill covers what it was refused (not remembered between processes)
                    key.dead_until = time.time() + float(reply.meta.get("retry_after", 600)) + 2
                attempts -= 1  # a refused call at the daily limit is not one of the retries
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
                record_usage(key.secret, body["model"], ok=True, status=resp.status, usage=u, headers=resp.headers, source="requirement_fulfillment")
                msg = data["choices"][0]["message"]
                calls = []
                for c in msg.get("tool_calls") or []:
                    try:
                        calls.append({"name": c["function"]["name"], "arguments": json.loads(c["function"].get("arguments") or "{}")})
                    except Exception:
                        calls.append({"name": c.get("function", {}).get("name", ""), "arguments": {}})
                reasoning = (msg.get("reasoning") or msg.get("reasoning_content") or "").strip()
                content_text = msg.get("content") or ""
                if not reasoning and "<think>" in content_text:
                    m = re.search(r"<think>(.*?)</think>", content_text, flags=re.DOTALL)
                    if m:
                        reasoning = m.group(1).strip()
                        content_text = re.sub(r"<think>.*?</think>", "", content_text, flags=re.DOTALL).strip()
                return Reply(text=content_text, reasoning=reasoning, prompt_tokens=u.get("prompt_tokens", 0), tool_calls=calls,
                             completion_tokens=u.get("completion_tokens", 0), model=data.get("model", body["model"]))
        except urllib.error.HTTPError as e:
            text = ""
            try:
                text = e.read().decode()[:600]
            except Exception:
                pass
            msg = re.sub(r"gsk_[A-Za-z0-9]+", "gsk_***", text)
            after = parse_wait(msg, default=8.0)
            low = re.sub(r"org_\w+", "org", msg).lower()  # an organisation id is random text: it must not match the checks below
            if e.code == 413 or "request too large" in low or "request_too_large" in low:
                return Reply(model=body["model"], error=f"HTTP {e.code}: {msg[:300]}", error_kind="too_large")
            if e.code == 429 and re.search(r"per day|\(tpd\)|\(rpd\)", low):
                record_usage(key.secret, body["model"], ok=False, status=429, headers=e.headers, error_kind="quota", error_text=msg, source="requirement_fulfillment")
                return Reply(model=body["model"], error=f"HTTP 429: {msg[:200]}", error_kind="quota", meta={"retry_after": after})
            if e.code == 429:
                record_usage(key.secret, body["model"], ok=False, status=429, headers=e.headers, error_kind="rate_limited", error_text=msg, source="requirement_fulfillment")
                return Reply(model=body["model"], error=f"HTTP 429: {msg[:200]}", error_kind="rate_limited", meta={"retry_after": after})
            if e.code == 400:
                return Reply(model=body["model"], error=f"HTTP 400: {msg[:300]}", error_kind="bad_request")
            return Reply(model=body["model"], error=f"HTTP {e.code}: {msg[:200]}", error_kind="server", meta={"retry_after": 5})
        except Exception as e:  # network, timeout, malformed body
            return Reply(model=body["model"], error=f"{type(e).__name__}: {str(e)[:160]}", error_kind="network", meta={"retry_after": 5})


def parse_wait(msg, default=8.0):
    """Seconds in a 'Please try again in 1h2m3.5s' (or '850ms') hint, plus a small margin."""
    m = re.search(r"try again in\s+((?:\d+(?:\.\d+)?(?:ms|h|m|s))+)", msg)
    if not m:
        return default
    total = 0.0
    for val, unit in re.findall(r"(\d+(?:\.\d+)?)(ms|h|m|s)", m.group(1)):
        total += float(val) * {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}[unit]
    return total + 0.5


def parse_json(text):
    """The first JSON object in a model reply, or None."""
    if not text:
        return None
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
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
