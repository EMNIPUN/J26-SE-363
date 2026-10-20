"""A normalised snapshot of an `assess` run, used to prove that a refactoring changed no output.

Volatile things are replaced (commit ids, contributor pseudonyms, timestamps, durations, temporary paths); everything else is compared:
stage statuses and details, the findings with their status, links, risk and probe results, the incomplete reasons, the decision trails,
the order of audit events, the report's headings and a digest of the whole normalised report.md.
"""

import hashlib
import json
import re
from pathlib import Path

_SHA = re.compile(r"\b[0-9a-f]{7,40}\b")
_PSEUDO = re.compile(r"\bC-[0-9a-f]{8}\b")
_TIME = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[^\s|]*(?: UTC)?")
_TMP = re.compile(r"[A-Za-z]:[\\/][^\s|\"')]*|/tmp/[^\s|\"')]*")


def norm(text) -> str:
    text = _TMP.sub("<path>", str(text))
    return _TIME.sub("<time>", _PSEUDO.sub("<pseudonym>", _SHA.sub("<sha>", text)))


def trail(entries):
    return [[e["step"], e["policy"], e["chosen"], norm(e["reason"]), norm(e.get("outcome")), bool(e.get("rejected"))] for e in entries]


def snapshot(report: dict, out: Path) -> dict:
    md = norm((out / "report.md").read_text(encoding="utf-8"))
    audit = [json.loads(x) for x in (out / "audit.jsonl").read_text(encoding="utf-8").splitlines()]
    return {
        "stages": [[s["stage"], s["status"], norm(s["detail"])] for s in report["run"]["stages"]],
        "complete": report["run"]["complete"],
        "incomplete_reasons": [norm(r) for r in report["run"]["incomplete_reasons"]],
        "llm_refused": report["run"]["llm_refused"],
        "findings": [{
            "group": f["group_id"], "rule": f["rule_id"], "status": f["status"], "confidence": f["confidence"], "evidence": f["evidence_ids"],
            "links": [[l["kind"], l["id"], l["status"], l["methods"]] for l in f["links"]],
            "risk": [f["risk"]["rank"], f["risk"]["score"]] if f["risk"] else None,
            "probe": [f["probe"]["decision"], f["probe"]["attempts"], f["probe"]["scores"]] if f["probe"] else None,
            "guidance": f["fix_guidance"]["id"] if f["fix_guidance"] else None,
        } for f in report["findings"]],
        "dismissed": report["dismissed"],
        "interpretation": report["interpretation"],
        "llm_usage": report["llm_usage"],
        "scan": {k: report["scan"][k] for k in ("languages", "complete", "skipped_tools", "warnings", "reused", "coverage_gaps")},
        "coverage": {c: v["level"] for c, v in report["scan"]["coverage"].items()},
        "governance": {k: report["governance"][k] for k in ("mode", "calls_checked", "calls_blocked", "violations_allowed_in_warn_only", "report_items_removed")},
        "scrutiny": {k: report["governance"]["scrutiny"][k] for k in ("level", "score", "escalated", "second_checks")},
        "decision_trail": {k: trail(v) for k, v in report["decision_trail"].items()},
        "audit_events": [e["event"] for e in audit],
        "report_md_headings": [l for l in md.splitlines() if l.startswith("#")],
        "report_md_sha256": hashlib.sha256(md.encode("utf-8")).hexdigest(),
    }
