"""Risk prioritisation: a transparent rule engine that ranks the interpreted findings. No LLM is involved in the score.

    python -m app.agents.security_assistant.risk <interpreted.json> [repo folder] [--out DIR]

score = 100 x sum(weight x factor) over six factors, each factor between 0 and 1:

  severity        0.30  the tool's own severity (a group of advisories uses its highest)
  category        0.15  how bad the kind of weakness usually is (V1 access control .. V5 dependencies)
  llm_status      0.20  confirmed 1.0, uncertain 0.4 (a down-weight); dismissed findings are not ranked at all
  llm_confidence  0.10  the model's confidence in its own status
  exposure        0.15  how reachable it is (a public workflow trigger, an HTTP endpoint, ...), by type of issue
  presence        0.10  in the current files 1.0, only in the git history 0.6 (needs the repo folder)

Every factor, its weight, its value and its contribution (100 x weight x value, rounded to 2 decimals) is stored, and the
score is the sum of the rounded contributions, so a reader can add the breakdown up and get exactly the score. The same input
always gives the same ranking. Outputs: risk.json and a "Risk prioritisation" section in report.md.

Exit code: 0 ok, 3 usage error.
"""

import argparse
import json
import sys
from pathlib import Path

from app.agents.security_assistant.interpreter.evidence import _safe_file
from app.agents.security_assistant.interpreter.redaction import redact_text
from app.agents.security_assistant.report import upsert_section

SECTION_MARK = "<!-- risk-prioritisation -->"
RISK_VERSION = "risk-v1"

WEIGHTS = {"severity": 0.30, "category": 0.15, "llm_status": 0.20, "llm_confidence": 0.10, "exposure": 0.15, "presence": 0.10}
CATEGORY_FACTOR = {"V1": 1.0, "V2": 1.0, "V4": 0.9, "V3": 0.8, "V5": 0.7}
STATUS_FACTOR = {"confirmed": 1.0, "uncertain": 0.4}  # dismissed is excluded, not scored
PRESENCE_FACTOR = {"current": 1.0, "history_only": 0.6}
UNKNOWN_SEVERITY = 0.4

SEVERITY_WORDS = {"critical": 1.0, "high": 0.8, "error": 0.8, "medium": 0.5, "moderate": 0.5, "warning": 0.5,
                  "low": 0.2, "note": 0.2, "info": 0.2, "recommendation": 0.2}
# Exposure by the type of issue (the guidance id the report already uses). The reason is shown with the score.
EXPOSURE = {
    "workflow-trigger": (1.0, "the workflow can be triggered by outside contributors"),
    "ownership-check": (0.9, "a request handler any logged-in user can reach"),
    "deny-by-default": (0.9, "every route is affected"),
    "add-spring-security": (0.9, "every route is affected"),
    "sql-injection": (0.9, "request input reaches a query"),
    "command-injection": (0.9, "request input reaches a command"),
    "default-password": (0.9, "anyone can try the default credentials"),
    "xss": (0.8, "attacker-controlled text is shown to other users"),
    "path-traversal": (0.8, "request input chooses a file"),
    "debug-and-actuator": (0.8, "an interface exposed by default"),
    "hardcoded-secret": (0.7, "anyone with the repository can read it"),
    "workflow-credentials": (0.7, "credentials available to the workflow"),
    "token-expiry": (0.6, "needs a stolen token first"),
    "cookie-flags": (0.6, "needs a network or script attacker"),
    "csrf-protection": (0.6, "needs a victim to visit a page"),
    "login-rate-limit": (0.6, "the login is reachable by anyone"),
    "workflow-permissions": (0.6, "a broader token than needed in CI"),
    "weak-password-hash": (0.5, "matters only after the database leaks"),
    "dependency-upgrade": (0.5, "reachability of the vulnerable code is not known"),
    "workflow-pinning": (0.5, "needs a compromised third-party action"),
    "workflow-lint": (0.4, "a quality or injection check in CI"),
}
DEFAULT_EXPOSURE = (0.5, "no specific exposure rule for this type of issue")
ENDPOINT_EXPOSURE = 0.9


def severity_factor(raw) -> tuple[float, str]:
    text = str(raw or "").strip().lower()
    if text in SEVERITY_WORDS:
        return SEVERITY_WORDS[text], f"tool severity '{text}'"
    try:
        score = float(text)  # CVSS-like number
    except ValueError:
        return UNKNOWN_SEVERITY, "the tool gave no usable severity"
    value = 1.0 if score >= 9 else 0.8 if score >= 7 else 0.5 if score >= 4 else 0.2
    return value, f"tool severity {text}"


def _group_severity(group: dict) -> tuple[float, str]:
    best = max((severity_factor(m.get("severity_tool")) for m in group["members"] or [group["representative"]]),
               key=lambda x: x[0], default=(UNKNOWN_SEVERITY, "the tool gave no usable severity"))
    return best[0], best[1] + (" (highest of the group)" if len(group["members"]) > 1 else "")


def presence_of(brief: dict, repo: Path | None) -> tuple[str, str]:
    """("current" | "history_only", detail). Only a finding that a scanner located in a commit (secrets) can be history
    only: it is when the file is gone or the line no longer holds anything that looks like a secret."""
    source = brief.get("source") or ""
    if not source.startswith("commit:"):
        return "current", "found by scanning the current files"
    if repo is None:
        return "current", "reported from a commit; not checked because no repo folder was given"
    path = _safe_file(Path(repo), brief.get("file_path"))
    if path is None:
        return "history_only", "the file is not in the current files"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    line = brief.get("line")
    now = lines[line - 1] if line and 1 <= line <= len(lines) else None
    if now is not None and redact_text(now) != now:
        return "current", "the secret is still in the current files"
    return "history_only", "the file exists but the line no longer holds the secret"


def exposure_of(brief: dict) -> tuple[float, str]:
    value, why = EXPOSURE.get(brief.get("fix_pattern") or "", DEFAULT_EXPOSURE)
    if brief.get("function_or_endpoint") and value < ENDPOINT_EXPOSURE:
        return ENDPOINT_EXPOSURE, f"reachable through the endpoint/function {brief['function_or_endpoint']}"
    return value, why


def score_group(group: dict, repo: Path | None = None) -> dict | None:
    """The scored entry for one interpreted group, or None for a dismissed one."""
    status = group["result"]["status"]
    if status not in STATUS_FACTOR:
        return None
    rep = group["representative"]
    sev, sev_why = _group_severity(group)
    presence, presence_why = presence_of(rep, repo)
    exposure, exposure_why = exposure_of(rep)
    values = {
        "severity": (sev, sev_why),
        "category": (CATEGORY_FACTOR.get(rep["category"], 0.5), f"category {rep['category']}"),
        "llm_status": (STATUS_FACTOR[status], f"the model judged it {status}"),
        "llm_confidence": (min(1.0, max(0.0, float(group["result"].get("confidence") or 0.0))),
                           "the model's confidence in its own status"),
        "exposure": (exposure, exposure_why),
        "presence": (PRESENCE_FACTOR[presence], presence_why),
    }
    factors = [{"factor": name, "weight": WEIGHTS[name], "value": round(value, 4), "contribution": round(100 * WEIGHTS[name] * value, 2),
                "detail": why} for name, (value, why) in values.items()]
    return {"group_id": group["group_id"], "category": rep["category"], "rule_id": rep["rule_id"], "file_path": rep["file_path"],
            "line": rep["line"], "package": group["package"], "findings_in_group": len(group["members"]), "status": status,
            "presence": presence, "factors": factors, "score": round(sum(f["contribution"] for f in factors), 2)}


def rank(doc: dict, repo: Path | None = None) -> dict:
    """The ranking of all interpreted groups: highest score first; ties go to the more serious category, then rule id, then
    group id, so the order never depends on the input order."""
    scored, excluded = [], []
    for g in doc["groups"]:
        entry = score_group(g, repo)
        if entry is None:
            excluded.append({"group_id": g["group_id"], "rule_id": g["representative"]["rule_id"],
                             "reason": f"the model judged it {g['result']['status']} (a false positive): not ranked"})
        else:
            scored.append(entry)
    scored.sort(key=lambda e: (-e["score"], -CATEGORY_FACTOR.get(e["category"], 0.5), e["rule_id"], e["group_id"]))
    for n, entry in enumerate(scored, 1):
        entry["rank"] = n
    return {"meta": {"risk_version": RISK_VERSION, "weights": WEIGHTS, "category_factor": CATEGORY_FACTOR,
                     "status_factor": STATUS_FACTOR, "presence_factor": PRESENCE_FACTOR, "repo_checked": repo is not None,
                     "uses_llm": False},
            "ranked": scored, "excluded": excluded}


# ---- output -------------------------------------------------------------------------------------------------------------------------------
def _cell(text) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def render_section(risk: dict) -> str:
    w = risk["meta"]["weights"]
    M = [SECTION_MARK, "## Risk prioritisation", "",
         "> A rule-based ranking, no LLM scoring. Score = 100 x sum of (weight x factor); the table shows each contribution, "
         "so the breakdown adds up to the score. Dismissed findings are not ranked; uncertain ones count with a lower weight. "
         "It helps to choose what to fix first; it is not a measured probability.", "",
         "Weights: " + ", ".join(f"{k} {v:g}" for k, v in w.items()) + ".", ""]
    if not risk["meta"]["repo_checked"]:
        M += ["No repo folder was given, so a secret reported from a commit is counted as present in the current files.", ""]
    if not risk["ranked"]:
        M += ["No confirmed or uncertain findings to rank.", ""]
    else:
        cols = list(w)
        M += ["| # | group | finding | where | status | score | " + " | ".join(cols) + " |",
              "|---|---|---|---|---|---|" + "---|" * len(cols)]
        for e in risk["ranked"]:
            where = (e["file_path"] or e["package"] or "-") + (f":{e['line']}" if e["line"] else "")
            by = {f["factor"]: f for f in e["factors"]}
            M.append(f"| {e['rank']} | {e['group_id']} | {e['category']} {_cell(e['rule_id'])} | {_cell(where)} | {e['status']} "
                     f"| **{e['score']:.2f}** | " + " | ".join(f"{by[c]['contribution']:.2f}" for c in cols) + " |")
        M += ["", "### Why each finding scored as it did", ""]
        for e in risk["ranked"]:
            M.append(f"**#{e['rank']} {e['group_id']} {_cell(e['rule_id'])}** (score {e['score']:.2f})")
            M += [f"- {f['factor']}: {f['value']:g} x {f['weight']:g} -> {f['contribution']:.2f} ({_cell(f['detail'])})"
                  for f in e["factors"]]
            M.append("")
    if risk["excluded"]:
        M += ["### Not ranked", ""] + [f"- {x['group_id']} {_cell(x['rule_id'])}: {x['reason']}" for x in risk["excluded"]] + [""]
    return "\n".join(M) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("interpreted", type=Path)
    ap.add_argument("repo", type=Path, nargs="?")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    try:
        doc = json.loads(args.interpreted.read_text(encoding="utf-8"))
        doc["groups"]
    except (OSError, ValueError, KeyError) as exc:
        print(f"cannot read the input: {exc}", file=sys.stderr)
        return 3
    if args.repo is not None and not args.repo.is_dir():
        print(f"not a directory: {args.repo}", file=sys.stderr)
        return 3
    out = args.out or args.interpreted.parent
    out.mkdir(parents=True, exist_ok=True)
    risk = rank(doc, args.repo)
    (out / "risk.json").write_text(json.dumps(risk, indent=2, ensure_ascii=False), encoding="utf-8")
    upsert_section(out / "report.md", SECTION_MARK, render_section(risk))
    print(f"{'#':<3}{'group':<6}{'score':>7}  {'status':<10}finding")
    for e in risk["ranked"]:
        print(f"{e['rank']:<3}{e['group_id']:<6}{e['score']:>7.2f}  {e['status']:<10}{e['category']} {e['rule_id'][:50]}")
    print(f"{len(risk['ranked'])} ranked, {len(risk['excluded'])} not ranked (dismissed). Wrote {out / 'risk.json'} and updated {out / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
