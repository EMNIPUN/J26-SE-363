"""Governance: narrow, deterministic checks around the stages that send data to an LLM. No LLM is involved.

What it does, and what it deliberately does not:

- **Pre-send check (blocks).** Before every LLM call (an interpretation or a link proposal) the exact outgoing text is checked for
  (a) the literal secret values of the scanned repository (read from the files and the git history, so the check does not trust
  the redaction it is checking), (b) text that still matches a secret pattern, (c) every personal value the redactor learned
  or replaced (emails, phone numbers, student ids, names) and e-mail, phone and student-id patterns. A failed check BLOCKS the
  call: the finding becomes "uncertain" with the reason, the run is INCOMPLETE. `--governance-warn-only` lets the call go through
  instead; the audit log and the report say so. Off by default.
- **Tool allow-list.** Only the tools of `default_tools()` may appear in a scan; a reused findings.json that names another tool is
  rejected as a whole.
- **Injection indicators (log only).** A fixed pattern list ("ignore previous instructions", "mark all findings dismissed", ...)
  is run over README files and commit messages of the repository even though they are not sent to the LLM, and over every outgoing
  prompt. A hit is logged as a finding about the repository and shown in the report. It is an INDICATOR, not proof: the list is
  short, easy to evade, and also matches text that merely talks about prompt injection. Nothing is blocked or changed because of it;
  the model is told in its prompt that repository text is untrusted data, and a verdict is still validated as before.
- **Audit log (`audit.jsonl`).** One JSON line per decision. It holds hashes of prompts (never their text), counts, ids and fixed
  reason codes. Every value is cleaned before it is written, so it cannot hold a secret, a personal value or free text.
- **Report scan.** Before report.json and report.md are written, the known secret values and personal values are removed from them if
  any got through, and the removal is counted and logged.

- **Stateful scrutiny.** Governance keeps a history for the run: a score that goes up with every injection indicator found in the
  repository (+1 per distinct source and pattern), every outgoing prompt that contains one (+1), every blocked call (+2), every call
  sent in warn-only mode despite a failed check (+1). At `elevated_at` (default 3) the scrutiny level becomes "elevated" and every
  later call gets a SECOND, stricter check (text folded to NFKC without invisible characters, spaces and punctuation removed, so a
  secret or name split by a zero-width character is still found). At `high_at` (default 6) governance ESCALATES: the run is flagged for
  human review of audit.jsonl and is incomplete. The level only goes up within a run. Every call and every change of level is a
  decision of the governance agent: chosen from a fixed list that the code validates (allow_call, allow_after_second_check, block_call,
  allow_call_warn_only, raise_scrutiny, escalate_to_reviewer), recorded in audit.jsonl and in the report's decision trail.

Governance never changes a verdict and never removes a finding. It only stops a call, records, raises its own scrutiny, or scrubs outgoing text.
"""

import hashlib
import json
import os
import re
import unicodedata
from collections import Counter
from pathlib import Path

from app.agents.security_assistant.agent_loop import Action, DecisionTrail, Policy, RulePolicy, select  # noqa: F401  (select: kept for callers)
from app.agents.security_assistant.graphs.governance_graph import PERSISTENT, build_gate_graph
from app.agents.security_assistant.pii import PIIRedactor
from app.agents.security_assistant.redaction import find_secret_values, redact_text
from app.agents.security_assistant.schemas import Category

AUDIT_FILE = "audit.jsonl"
LEVELS = ("normal", "elevated", "high")
POINTS = {"repo_indicator": 1, "prompt_indicator": 1, "blocked_call": 2, "second_check_blocked": 2, "violation_allowed": 1}
ALLOWED_TOOLS = frozenset({"config-scan", "gitleaks", "trufflehog", "osv-scanner", "npm-audit", "pip-audit", "actionlint", "zizmor", "codeql"})
MIN_SECRET_LEN = 6
MAX_SECRET_VALUES = 300
MAX_README_BYTES = 200_000
MAX_COMMITS = 2000

# Injection indicators. A short list on purpose: it is an indicator that something in the repository talks to the model, not proof.
INJECTION_PATTERNS: tuple[tuple[str, re.Pattern], ...] = tuple((pid, re.compile(rx, re.I | re.M)) for pid, rx in (
    ("ignore-previous-instructions", r"\bignore\s+(?:all\s+|any\s+|the\s+|your\s+)?(?:previous|prior|above|earlier)\s+(?:instructions?|prompts?|rules?|messages?)"),
    ("disregard-instructions", r"\b(?:disregard|forget|override)\s+(?:all\s+|any\s+|the\s+|your\s+)?(?:previous\s+|prior\s+|above\s+|system\s+|earlier\s+)?(?:instructions?|prompts?|rules?)"),
    ("mark-findings-dismissed", r"\b(?:mark|set|label|report|classify|treat)\s+(?:all\s+|every\s+|each\s+|these\s+|the\s+)?(?:findings?|issues?|vulnerabilit(?:y|ies)|alerts?)\s+(?:as\s+|to\s+)?(?:dismissed|false[\s-]positives?|safe|fixed|resolved|not\s+a\s+problem)"),
    ("answer-with-status", r"\b(?:reply|respond|answer|output)\s+(?:only\s+)?with\s+(?:status\s+)?[\"']?(?:dismissed|confirmed|uncertain)\b"),
    ("role-change", r"\byou\s+are\s+now\b|\bact\s+as\s+(?:an?\s+)?(?:system|assistant|admin|reviewer)\b|\bfrom\s+now\s+on\s+you\b"),
    ("fake-system-message", r"^\s*(?:system|assistant|developer)\s*:|<\\?\s*/?\s*(?:system|assistant|evidence)\b|\[\s*(?:system|inst)\s*\]|\bBEGIN\s+SYSTEM\b"),
    ("addresses-the-reviewer", r"\b(?:notes?|messages?|instructions?)\s+(?:to|for)\s+(?:the\s+)?(?:ai|llm|model|automated\s+reviewers?|automated\s+tools?|assistant)\b|\bfor\s+ai\s+tools?\b"),
    ("tell-not-to-report", r"\bdo\s+not\s+(?:report|flag|mention)\b.{0,40}\b(?:findings?|vulnerabilit\w*|issues?)"),
))
_HARNESS = re.compile(r'<evidence id="E\d+" kind="\w+" label="[^"]*">|</evidence>')
_README = re.compile(r"(?i)^(?:readme|contributing|changelog)[^/\\]*$|^[^/\\]+\.md$")
_REASON_CODES = (("cited evidence ids", "unknown_evidence_id"), ("a confirmed or dismissed verdict must cite", "no_evidence_id"),
                 ("the model dismissed a secret finding", "v4_dismissal_unsupported"))


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ[name])) if os.environ.get(name) else default
    except ValueError:
        return default


def _fold(text: str) -> str:
    """NFKC, no invisible format characters, lower case: the form in which an obfuscated value looks like itself again."""
    return "".join(c for c in unicodedata.normalize("NFKC", text or "") if unicodedata.category(c) != "Cf").lower()


def _squeeze(text: str) -> str:
    return "".join(c for c in _fold(text) if c.isalnum())


class GovernanceBlock(Exception):
    """A governance check stopped an LLM call. `code` is a fixed reason code; the message never contains the data that triggered it."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


class ToolNotAllowed(ValueError):
    """A scan names a tool that is not on the allow-list."""


def injection_indicators(text: str) -> dict[str, int]:
    """{pattern id: hits} for the injection patterns found in `text` (harness tags of the prompt itself are ignored)."""
    text = _HARNESS.sub("", text or "")
    hits = {pid: len(rx.findall(text)) for pid, rx in INJECTION_PATTERNS}
    return {pid: n for pid, n in hits.items() if n}


def prompt_hash(system: str, user: str) -> str:
    return hashlib.sha256((system + "\n\x1f\n" + user).encode("utf-8")).hexdigest()


def known_secret_values(repo: Path | None, findings) -> set[str]:
    """The literal secret values of the V4 findings, read from the files (and, for a secret only in the history, from the commit the
    scanner named). Held in memory for the pre-send check; never written anywhere."""
    from app.agents.security_assistant.interpreter.evidence import _git_read, _safe_file  # lazy: the interpreter package imports this module

    out: set[str] = set()
    if repo is None:
        return out
    repo = Path(repo)
    for f in findings:
        if f.category is not Category.V4 or not f.file_path or f.line is None or len(out) >= MAX_SECRET_VALUES:
            continue
        texts = []
        path = _safe_file(repo, f.file_path)
        if path is not None:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            texts.append("\n".join(lines[max(0, f.line - 2):f.line + 1]))  # key pairs sit on neighbouring lines
        m = re.fullmatch(r"commit:([0-9a-f]{7,40})", f.source or "")
        if m and (repo / ".git").exists():
            blob = _git_read(repo, "show", "--no-textconv", f"{m.group(1)}:{f.file_path}")
            if blob:
                lines = blob.splitlines()
                texts.append("\n".join(lines[max(0, f.line - 2):f.line + 1]))
        for text in texts:
            out.update(v for v in find_secret_values(text) if len(v) >= MIN_SECRET_LEN)
    return out


class AuditLog:
    """One JSON line per decision. Values are cleaned before they are written: strings are cut, secrets and personal data removed,
    so the file cannot hold a prompt, a secret, a name or an e-mail address."""

    def __init__(self, path: Path | None, append: bool = False):
        self.path, self.seq = (Path(path) if path else None), 0
        self.forbidden: set[str] = set()  # literal secrets and personal values that must never appear in the file
        self.pii: PIIRedactor | None = None
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if append and self.path.exists():  # a second command of the same output folder continues the log
                self.seq = len(self.path.read_text(encoding="utf-8").splitlines())
            else:
                self.path.write_text("", encoding="utf-8")  # a new run starts a new log; within a run lines are only appended

    def _clean(self, value):
        if isinstance(value, bool) or value is None or isinstance(value, (int, float)):
            return value
        if isinstance(value, (list, tuple, set)):
            return [self._clean(v) for v in list(value)[:60]]
        if isinstance(value, dict):
            return {str(k)[:60]: self._clean(v) for k, v in list(value.items())[:60]}
        text = " ".join(str(value).split())[:2000]  # clean first, cut afterwards: a cut must never leave half a secret behind
        text = redact_text(text)
        if self.pii is not None:
            text = self.pii.redact_plain(text)
        for secret in sorted(self.forbidden, key=len, reverse=True):
            if secret and secret.lower() in text.lower():
                text = re.sub(re.escape(secret), "[withheld]", text, flags=re.I)
        return text[:200]

    def record(self, event: str, **fields) -> dict:
        entry = {"seq": self.seq, "event": event, **{k: self._clean(v) for k, v in fields.items()}}
        self.seq += 1
        if self.path is not None:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry


class _GateField:
    """An attribute of Governance that is a key of the gate graph's state: reading and writing it reads and writes `Governance.gstate`."""

    def __init__(self, name: str):
        self.name = name

    def __get__(self, obj, cls=None):
        return self if obj is None else obj.gstate[self.name]

    def __set__(self, obj, value):
        obj.gstate[self.name] = value


class Governance:
    level = _GateField("level")
    score = _GateField("score")
    history = _GateField("history")
    checked = _GateField("checked")
    blocked = _GateField("blocked")
    allowed = _GateField("allowed")
    repo_indicator_count = _GateField("repo_indicator_count")
    prompt_with_indicators = _GateField("prompt_with_indicators")
    second_checks = _GateField("second_checks")
    second_check_blocks = _GateField("second_check_blocks")
    escalated = _GateField("escalated")
    escalation_reason = _GateField("escalation_reason")

    def __init__(self, out_dir: Path | None = None, *, warn_only: bool = False, pii: PIIRedactor | None = None,
                 secret_values: set[str] | None = None, elevated_at: int | None = None, high_at: int | None = None,
                 policy: Policy | None = None):
        self.audit = AuditLog(Path(out_dir) / AUDIT_FILE if out_dir else None)
        # the memory of the run: the state of the gate graph (graphs/governance_graph.py), carried from one invocation to the next
        self.gstate: dict = {"level": "normal", "score": 0, "history": [], "checked": 0, "blocked": 0, "allowed": 0, "repo_indicator_count": 0,
                             "prompt_with_indicators": 0, "second_checks": 0, "second_check_blocks": 0, "escalated": False,
                             "escalation_reason": None, "step": 0}
        self.warn_only = warn_only
        self.pii = pii
        self.audit.pii = pii
        self.secrets: set[str] = set()
        self.set_secret_values(secret_values or set())
        self.scrubbed = 0
        self.tool_check: dict = {}
        self.indicators: list[dict] = []
        self.prompt_indicators: Counter = Counter()
        self.repo_files_scanned = 0
        # the state the governance agent keeps for the run
        self.elevated_at = elevated_at or _env_int("SECURITY_ASSISTANT_GOVERNANCE_ELEVATED_AT", 3)
        self.high_at = max(self.elevated_at + 1, high_at or _env_int("SECURITY_ASSISTANT_GOVERNANCE_HIGH_AT", 6))
        self.policy, self._rules = policy or RulePolicy(), RulePolicy()
        self.trail = DecisionTrail("governance", self.audit)
        self._gate = build_gate_graph(self)  # the stateful gate; compiled once, invoked before every LLM call

    # ---- set up -------------------------------------------------------------------------------------------------------------------
    def set_secret_values(self, values: set[str]) -> None:
        self.secrets = {v for v in values if len(v) >= MIN_SECRET_LEN}
        self.audit.forbidden = set(self.secrets)

    def start(self, **fields) -> None:
        self.audit.record("run_start", governance="warn-only" if self.warn_only else "enforce", warn_only=self.warn_only, **fields)

    # ---- state: score, scrutiny level, escalation --------------------------------------------------------------------------------
    def state(self) -> dict:
        """The summary of the gate's state, as the policy sees it."""
        return {"level": self.level, "score": self.score, "elevated_at": self.elevated_at, "high_at": self.high_at,
                "calls_checked": self.checked, "calls_blocked": self.blocked, "repo_indicators": self.repo_indicator_count,
                "prompts_with_indicators": self.prompt_with_indicators, "second_checks": self.second_checks}

    def _start_state(self, event: dict) -> dict:
        """The input of one pass through the gate: the state the last pass ended with, the thresholds, and the event."""
        return {**self.gstate, "elevated_at": self.elevated_at, "high_at": self.high_at, "noted": False, "phase": "pre",
                "raise_needed": False, "escalate_needed": False, "block": None, **event}

    def _store(self, final: dict) -> None:
        """Keep the persistent part of the final state of a pass: the gate remembers the run."""
        for key in PERSISTENT:
            value = final[key]
            self.gstate[key] = list(value) if isinstance(value, list) else value

    def _invoke(self, event: dict) -> dict:
        """One pass through the gate graph, starting from the state the last pass ended with."""
        final = self._gate.invoke(self._start_state(event), {"recursion_limit": 60})
        self._store(final)
        return final

    def _strict_violations(self, system: str, user: str) -> list[tuple[str, str]]:
        """The second check, run at elevated scrutiny: the same questions asked of the folded text (see _fold)."""
        out: list[tuple[str, str]] = []
        text = system + "\n" + user
        folded, squeezed = _fold(text), _squeeze(text)
        if any((_squeeze(s) in squeezed) if len(s) >= 12 else (s.lower() in folded) for s in self.secrets):
            out.append(("second_check_secret", "a secret value, hidden by invisible characters, spacing or look-alike characters, is in the outgoing text"))
        if self.pii is not None:
            evidence = user[user.index("<evidence"):] if "<evidence" in user else user
            f_evidence, s_evidence = _fold(evidence), _squeeze(evidence)
            for original in self.pii.originals():
                hit = (_squeeze(original) in s_evidence) if len(original) >= 8 else bool(
                    re.search(rf"(?<![a-z0-9]){re.escape(_fold(original))}(?![a-z0-9])", f_evidence))
                if hit:
                    out.append(("second_check_personal", "a personal value, hidden by invisible characters or spacing, is in the outgoing evidence"))
                    break
        return out

    # ---- tool allow-list --------------------------------------------------------------------------------------------------------
    def check_tools(self, names, source: str) -> list[str]:
        """Names that are not on the allow-list (sorted). Recorded either way."""
        names = sorted({str(n) for n in names if n})
        rejected = [n for n in names if n not in ALLOWED_TOOLS]
        self.tool_check = {"source": source, "tools": names, "rejected": rejected}
        self.audit.record("tool_allowlist", source=source, tools=names, rejected=rejected, decision="rejected" if rejected else "allowed")
        return rejected

    # ---- the repository: injection indicators in files that are not sent ------------------------------------------------------
    def scan_repo(self, repo: Path | None) -> list[dict]:
        """README-like files and commit messages, scanned locally. Hits are findings about the repository, not about its code."""
        from app.agents.security_assistant.interpreter.evidence import _git_read, _safe_file  # lazy, see known_secret_values

        hits: list[dict] = []
        if repo is None:
            return hits
        repo, scanned = Path(repo), 0
        candidates = [p for base in (repo, repo / "docs", repo / "doc") if base.is_dir() for p in sorted(base.iterdir())
                      if p.is_file() and _README.match(p.name)][:30]
        for path in candidates:
            if _safe_file(repo, str(path.relative_to(repo))) is None or path.stat().st_size > MAX_README_BYTES:
                continue
            scanned += 1
            for pid, n in injection_indicators(path.read_text(encoding="utf-8", errors="replace")).items():
                hits.append({"kind": "readme", "source": str(path.relative_to(repo)).replace("\\", "/"), "pattern": pid, "count": n})
        if (repo / ".git").exists():
            log = _git_read(repo, "log", "--all", f"-n{MAX_COMMITS}", "--format=%H%x1f%B%x1e", timeout=40) or ""
            for record in log.split("\x1e"):
                sha, _sep, message = record.strip().partition("\x1f")
                if not sha:
                    continue
                scanned += 1
                for pid, n in injection_indicators(message).items():
                    hits.append({"kind": "commit message", "source": f"commit {sha[:7]}", "pattern": pid, "count": n})
        self.repo_files_scanned += scanned
        self.indicators.extend(hits)
        distinct = len({(h["source"], h["pattern"]) for h in hits})
        self.repo_indicator_count += distinct
        self.audit.record("repo_scan", sources_scanned=scanned, indicators=len(hits))
        for h in hits:
            self.audit.record("injection_indicator", kind=h["kind"], source=h["source"], pattern=h["pattern"], count=h["count"],
                              effect="logged only; nothing was blocked or changed")
        if distinct:
            self._invoke({"event": "repo", "distinct": distinct})  # repeated indicators raise the scrutiny of every later call
        return hits

    # ---- before a call ------------------------------------------------------------------------------------------------------------
    def _violations(self, system: str, user: str) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        text = system + "\n" + user
        if any(s in text for s in self.secrets):
            out.append(("secret_value_in_prompt", "a secret value of the scanned repository is in the outgoing text"))
        if redact_text(text) != text:
            out.append(("secret_pattern_in_prompt", "the outgoing text still matches a secret pattern"))
        evidence = user[user.index("<evidence"):] if "<evidence" in user else user  # static instructions are not personal data
        if self.pii is not None:
            from app.agents.security_assistant.pii import _EMAIL, _PHONE

            if any(re.search(rf"(?<![A-Za-z0-9]){re.escape(o)}(?![A-Za-z0-9])", evidence, re.I) for o in self.pii.originals()):
                out.append(("personal_value_in_prompt", "a personal value the redactor knows is in the outgoing evidence"))
            elif (_EMAIL.search(evidence) or self.pii.student_id.search(evidence)
                  or any(sum(c.isdigit() for c in m.group(0)) >= 9 for m in _PHONE.finditer(evidence))):
                out.append(("personal_pattern_in_prompt", "an e-mail address, phone number or student id is in the outgoing evidence"))
        return out

    def pre_send(self, kind: str, *, finding_key: str, category: str, rule_id: str, system: str, user: str, offered_ids,
                 model: str | None = None, prompt_version: str | None = None, seed: int | None = None) -> str:
        """Pass one outgoing prompt through the gate graph. Returns the prompt's hash; raises GovernanceBlock when the gate decided to block it.
        The gate chooses from the options its checks leave valid: with a failed check there is no 'allow' option."""
        final = self._invoke({"event": "call", "kind": kind, "finding_key": finding_key, "category": category, "rule_id": rule_id,
                              "system": system, "user": user, "offered_ids": list(offered_ids), "model": model,
                              "prompt_version": prompt_version, "seed": seed})
        if final.get("block"):
            raise GovernanceBlock(final["block"]["code"], final["block"]["message"])
        return final["digest"]

    # ---- after a call ----------------------------------------------------------------------------------------------------------------
    def post_call(self, kind: str, *, finding_key: str, prompt_sha256: str, offered_ids, result) -> None:
        reason = getattr(result, "downgrade_reason", None) or ""
        code = next((c for prefix, c in _REASON_CODES if reason.startswith(prefix)), "other" if reason else None)
        cited = list(getattr(result, "evidence_ids", []) or [])
        call = getattr(result, "call", None)
        self.audit.record(
            "llm_result", call=kind, finding_key=finding_key, prompt_sha256=prompt_sha256,
            verdict_from_model=getattr(result, "original_status", None) or result.status, verdict_final=result.status,
            downgraded=bool(getattr(result, "downgraded", False)), downgrade_code=code, evidence_ids_cited=cited,
            evidence_ids_valid=all(i in set(offered_ids) for i in cited), llm_error=bool(getattr(result, "error", None)),
            output_rejected=bool(getattr(result, "output_rejected", False)),
            prompt_tokens=getattr(call, "prompt_tokens", None), completion_tokens=getattr(call, "completion_tokens", None),
            attempts=getattr(call, "attempts", None), seed=getattr(call, "seed", None))

    def blocked_result_event(self, finding_key: str, code: str) -> None:
        self.audit.record("llm_result", call="blocked", finding_key=finding_key, verdict_final="uncertain", downgrade_code=code)

    # ---- the report ------------------------------------------------------------------------------------------------------------------
    def _report_values(self) -> list[str]:
        """The values that must not be in a report: secrets and full personal values (emails, phones, ids, full names)."""
        full = set()
        if self.pii is not None:
            full = {v for v in self.pii.mapping.values() if len(v) >= 3} | {v for v in self.pii._names.values() if len(v) >= 3}
        return sorted(self.secrets | full, key=len, reverse=True)

    def _patterns(self):
        """E-mail, phone and student-id patterns of the personal-data redactor: values the run never saw (one the model made up) are caught too."""
        if self.pii is None:
            return []
        from app.agents.security_assistant.pii import _EMAIL, _PHONE

        return [(_EMAIL, None), (self.pii.student_id, None), (_PHONE, 9)]  # (pattern, minimum number of digits or None)

    @staticmethod
    def _hit(match, digits) -> bool:
        return digits is None or sum(c.isdigit() for c in match.group(0)) >= digits

    def count_leaks(self, text: str) -> int:
        """How many known secret or personal values, or personal-data patterns, `text` contains (changes nothing, logs nothing)."""
        n = 0
        for value in self._report_values():
            n += len(re.findall(rf"(?<![A-Za-z0-9]){re.escape(value)}(?![A-Za-z0-9])", text, flags=re.I))
        for pattern, digits in self._patterns():
            n += sum(self._hit(m, digits) for m in pattern.finditer(text))
        return n

    def scrub(self, text: str, label: str) -> str:
        """Remove known secret values, full personal values and personal-data patterns from a report before it is written, and log how many."""
        removed = 0
        for value in self._report_values():
            text, n = re.subn(rf"(?<![A-Za-z0-9]){re.escape(value)}(?![A-Za-z0-9])", "[removed by governance]", text, flags=re.I)
            removed += n
        for pattern, digits in self._patterns():
            count = [0]

            def repl(m, digits=digits, count=count):
                if self._hit(m, digits):
                    count[0] += 1
                    return "[removed by governance]"
                return m.group(0)

            text = pattern.sub(repl, text)
            removed += count[0]
        self.audit.record("report_scan", file=label, items_removed=removed, decision="scrubbed" if removed else "clean")
        return text

    def end(self, *, complete: bool, reasons: int) -> None:
        self.audit.record("run_end", calls_checked=self.checked, calls_blocked=self.blocked, violations_allowed_in_warn_only=self.allowed,
                          injection_indicators_in_repo=len(self.indicators), report_items_removed=self.scrubbed,
                          scrutiny=self.level, score=self.score, escalated=self.escalated, run_complete=complete, incomplete_reasons=reasons)

    def summary(self) -> dict:
        return {"mode": "warn-only" if self.warn_only else "enforce", "audit_file": AUDIT_FILE, "audit_lines": self.audit.seq,
                "calls_checked": self.checked, "calls_blocked": self.blocked, "violations_allowed_in_warn_only": self.allowed,
                "tool_check": self.tool_check, "injection_indicators": self.indicators, "repo_sources_scanned": self.repo_files_scanned,
                "prompt_indicator_patterns": dict(self.prompt_indicators), "report_items_removed": self.scrubbed,
                "pattern_ids": [pid for pid, _ in INJECTION_PATTERNS],
                "scrutiny": {"level": self.level, "score": self.score, "elevated_at": self.elevated_at, "high_at": self.high_at,
                             "second_checks": self.second_checks, "second_check_blocks": self.second_check_blocks,
                             "escalated": self.escalated, "escalation_reason": self.escalation_reason, "history": self.history}}


def render_section(summary: dict) -> str:
    s = summary
    M = ["## Governance", "",
         "> Deterministic checks around the LLM stages (no LLM). Governance never changes a verdict and never removes a finding; it can "
         "stop a call, record, or remove a leaked value from this report.", ""]
    if s["mode"] == "warn-only":
        M += [f"> **WARN-ONLY MODE (`--governance-warn-only`).** A failed secret or personal-data check did not stop the call; "
              f"{s['violations_allowed_in_warn_only']} call(s) were sent although a check failed (see {s['audit_file']}).", ""]
    sc = s.get("scrutiny")
    if sc and sc["escalated"]:
        M += [f"> **ESCALATED FOR HUMAN REVIEW.** {sc['escalation_reason']}. A person should read `{s['audit_file']}` before relying on this run; "
              "the run is marked incomplete.", ""]
    M += [f"- **Mode:** {s['mode']}; **audit log:** `{s['audit_file']}` ({s['audit_lines']} lines: hashes, counts and reason codes only, never prompt text).",
          f"- **LLM calls checked before sending:** {s['calls_checked']}; **blocked:** {s['calls_blocked']}"
          + (f"; **sent despite a failed check (warn-only):** {s['violations_allowed_in_warn_only']}" if s["mode"] == "warn-only" else "") + ".",
          f"- **Tool allow-list:** " + ("not checked" if not s["tool_check"] else
                                        f"{len(s['tool_check']['tools'])} tool(s) from {s['tool_check']['source']}; "
                                        + (f"REJECTED: {', '.join(s['tool_check']['rejected'])}" if s["tool_check"]["rejected"] else "all allowed")) + ".",
          f"- **Report scan:** {s['report_items_removed']} secret or personal value(s) removed from the report files before writing."]
    if sc:
        M.append(f"- **Scrutiny:** {sc['level']} (score {sc['score']}; elevated at {sc['elevated_at']}, high at {sc['high_at']}). From 'elevated' every call "
                 f"gets a second, stricter check: {sc['second_checks']} second check(s) run, {sc['second_check_blocks']} call(s) stopped by one. "
                 "The score rises with injection indicators and blocked calls and never falls within a run; scrutiny never changes a verdict.")
    M.append("")
    M += ["### Prompt-injection indicators in the repository", "",
          "> An **indicator, not proof.** A fixed list of phrases (for example \"ignore previous instructions\", \"mark all findings dismissed\") "
          "is searched for in README files and commit messages, which are not sent to the LLM, and in every outgoing prompt. A hit means "
          "someone wrote text that addresses a reviewer or a model. Nothing was blocked or changed because of it; the list is short, easy to "
          "evade, and can also match text that only talks about prompt injection.", ""]
    if s["injection_indicators"]:
        M += ["| where | kind | pattern | hits |", "|---|---|---|---|"]
        M += [f"| {h['source']} | {h['kind']} | {h['pattern']} | {h['count']} |" for h in s["injection_indicators"]]
    else:
        M.append(f"None found in {s['repo_sources_scanned']} README file(s) and commit message(s).")
    if s["prompt_indicator_patterns"]:
        M += ["", "Patterns also found in outgoing prompts: " + ", ".join(sorted(s["prompt_indicator_patterns"])) + "."]
    return "\n".join(M) + "\n"
