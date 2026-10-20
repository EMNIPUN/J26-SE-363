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

Governance never changes a verdict and never removes a finding. It only stops a call, records, or scrubs outgoing text.
"""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from app.agents.security_assistant.interpreter.evidence import _git_read, _safe_file
from app.agents.security_assistant.pii import PIIRedactor
from app.agents.security_assistant.redaction import find_secret_values, redact_text
from app.agents.security_assistant.schemas import Category

AUDIT_FILE = "audit.jsonl"
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


class Governance:
    def __init__(self, out_dir: Path | None = None, *, warn_only: bool = False, pii: PIIRedactor | None = None,
                 secret_values: set[str] | None = None):
        self.audit = AuditLog(Path(out_dir) / AUDIT_FILE if out_dir else None)
        self.warn_only = warn_only
        self.pii = pii
        self.audit.pii = pii
        self.secrets: set[str] = set()
        self.set_secret_values(secret_values or set())
        self.checked = self.blocked = self.allowed = self.scrubbed = 0
        self.tool_check: dict = {}
        self.indicators: list[dict] = []
        self.prompt_indicators: Counter = Counter()
        self.repo_files_scanned = 0

    # ---- set up -------------------------------------------------------------------------------------------------------------------
    def set_secret_values(self, values: set[str]) -> None:
        self.secrets = {v for v in values if len(v) >= MIN_SECRET_LEN}
        self.audit.forbidden = set(self.secrets)

    def start(self, **fields) -> None:
        self.audit.record("run_start", governance="warn-only" if self.warn_only else "enforce", warn_only=self.warn_only, **fields)

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
        self.audit.record("repo_scan", sources_scanned=scanned, indicators=len(hits))
        for h in hits:
            self.audit.record("injection_indicator", kind=h["kind"], source=h["source"], pattern=h["pattern"], count=h["count"],
                              effect="logged only; nothing was blocked or changed")
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
        """Check one outgoing prompt. Returns its hash. Raises GovernanceBlock when a check fails (unless warn-only)."""
        digest = prompt_hash(system, user)
        violations = self._violations(system, user)
        indicators = injection_indicators(_HARNESS.sub("", user))
        self.prompt_indicators.update(indicators.keys())
        self.checked += 1
        decision = "send"
        if violations:
            decision = "send-warn-only" if self.warn_only else "blocked"
        self.audit.record("pre_send_check", call=kind, finding_key=finding_key, category=category, rule_id=rule_id,
                          prompt_sha256=digest, prompt_chars=len(system) + len(user), evidence_ids_offered=sorted(offered_ids),
                          model=model, prompt_version=prompt_version, seed=seed,
                          secret_check="fail" if any(c.startswith("secret") for c, _ in violations) else "pass",
                          personal_data_check="fail" if any(c.startswith("personal") for c, _ in violations) else "pass",
                          violations=[c for c, _ in violations], injection_indicators=indicators, decision=decision)
        if violations:
            if self.warn_only:
                self.allowed += 1
            else:
                self.blocked += 1
                code, message = violations[0]
                raise GovernanceBlock(code, f"governance blocked the call before it was sent: {message}")
        return digest

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

    def count_leaks(self, text: str) -> int:
        """How many known secret or personal values `text` contains (changes nothing, logs nothing)."""
        n = 0
        for value in self._report_values():
            n += len(re.findall(rf"(?<![A-Za-z0-9]){re.escape(value)}(?![A-Za-z0-9])", text, flags=re.I))
        return n

    def scrub(self, text: str, label: str) -> str:
        """Remove known secret values and full personal values from a report before it is written, and log how many."""
        removed = 0
        for value in self._report_values():
            text, n = re.subn(rf"(?<![A-Za-z0-9]){re.escape(value)}(?![A-Za-z0-9])", "[removed by governance]", text, flags=re.I)
            removed += n
        self.audit.record("report_scan", file=label, items_removed=removed, decision="scrubbed" if removed else "clean")
        return text

    def end(self, *, complete: bool, reasons: int) -> None:
        self.audit.record("run_end", calls_checked=self.checked, calls_blocked=self.blocked, violations_allowed_in_warn_only=self.allowed,
                          injection_indicators_in_repo=len(self.indicators), report_items_removed=self.scrubbed,
                          run_complete=complete, incomplete_reasons=reasons)

    def summary(self) -> dict:
        return {"mode": "warn-only" if self.warn_only else "enforce", "audit_file": AUDIT_FILE, "audit_lines": self.audit.seq,
                "calls_checked": self.checked, "calls_blocked": self.blocked, "violations_allowed_in_warn_only": self.allowed,
                "tool_check": self.tool_check, "injection_indicators": self.indicators, "repo_sources_scanned": self.repo_files_scanned,
                "prompt_indicator_patterns": dict(self.prompt_indicators), "report_items_removed": self.scrubbed,
                "pattern_ids": [pid for pid, _ in INJECTION_PATTERNS]}


def render_section(summary: dict) -> str:
    s = summary
    M = ["## Governance", "",
         "> Deterministic checks around the LLM stages (no LLM). Governance never changes a verdict and never removes a finding; it can "
         "stop a call, record, or remove a leaked value from this report.", ""]
    if s["mode"] == "warn-only":
        M += [f"> **WARN-ONLY MODE (`--governance-warn-only`).** A failed secret or personal-data check did not stop the call; "
              f"{s['violations_allowed_in_warn_only']} call(s) were sent although a check failed (see {s['audit_file']}).", ""]
    M += [f"- **Mode:** {s['mode']}; **audit log:** `{s['audit_file']}` ({s['audit_lines']} lines: hashes, counts and reason codes only, never prompt text).",
          f"- **LLM calls checked before sending:** {s['calls_checked']}; **blocked:** {s['calls_blocked']}"
          + (f"; **sent despite a failed check (warn-only):** {s['violations_allowed_in_warn_only']}" if s["mode"] == "warn-only" else "") + ".",
          f"- **Tool allow-list:** " + ("not checked" if not s["tool_check"] else
                                        f"{len(s['tool_check']['tools'])} tool(s) from {s['tool_check']['source']}; "
                                        + (f"REJECTED: {', '.join(s['tool_check']['rejected'])}" if s["tool_check"]["rejected"] else "all allowed")) + ".",
          f"- **Report scan:** {s['report_items_removed']} secret or personal value(s) removed from the report files before writing.", ""]
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
