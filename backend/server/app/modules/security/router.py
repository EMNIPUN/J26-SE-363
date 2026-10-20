"""Security Assistant results, read-only.

GET /api/v1/security-assistant/teams/{team}/runs                 the runs of a team (newest first)
GET /api/v1/security-assistant/teams/{team}/students             the students of a team (lecturers and admins)
GET /api/v1/security-assistant/teams/{team}/runs/{run}           provenance, stages, tool runs, coverage, counts
GET .../runs/{run}/findings[?category=&status=&mine=]             the findings; .../findings/{group_id} one finding
GET .../runs/{run}/learning | agents | workflow                  mock Tutor results, agent trails and governance, graphs with the nodes that ran
GET .../runs/{run}/audit                                         the audit log (lecturers and admins)
GET .../evidence | compare?a=&b=                                 scanner only vs scanner plus LLM, RQ1, limitations | a diff of two runs

`{team}` is the team's id or code, with the same rule as everywhere else: members only, anyone else gets 404. Nothing here writes
to the database or to the result folders, and nothing starts a scan. The data comes from `reader.ResultsReader`.
"""

import csv
import io
import re
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from shared.contracts import UserRole
from sqlalchemy.orm import Session

from app.api.deps import Account, get_onboarded_account, require_account_role
from app.core.config import settings
from app.core.errors import ApiError, not_found
from app.database.session import get_db
from app.models.group import Group, MemberRole
from app.modules.security.reader import NotFound, ResultsReader, counts
from app.services import team_rules as rules
from app.services import teams

router = APIRouter(prefix="/security-assistant", tags=["Security Assistant"])

SAMPLE_DIR = Path(__file__).parent / "sample_results"

Onboarded = Annotated[Account, Depends(get_onboarded_account)]
StaffOnly = Annotated[Account, Depends(require_account_role(UserRole.LECTURER, UserRole.ADMIN))]
Db = Annotated[Session, Depends(get_db)]


def get_reader() -> ResultsReader:
    """The result folders, or the checked-in sample when SECURITY_ASSISTANT_DEMO_MODE is on (never switched on by itself)."""
    return ResultsReader(SAMPLE_DIR if settings.SECURITY_ASSISTANT_DEMO_MODE else settings.security_assistant_results_dir)


Reader = Annotated[ResultsReader, Depends(get_reader)]


def demo_data() -> bool:
    return bool(settings.SECURITY_ASSISTANT_DEMO_MODE)


def team_access(db: Session, team: str, account: Account) -> Group:
    """The team if this person belongs to it (or is an administrator); otherwise 404."""
    group, _ = teams.team_for(db, team, account.user, is_admin=account.role is UserRole.ADMIN)
    return group


def load_run(reader: ResultsReader, group: Group, run_id: str) -> dict:
    try:
        return reader.run(group.code, run_id)
    except NotFound:
        raise not_found("Run not found") from None


def viewer_email(group: Group, account: Account, student: str | None) -> str | None:
    """Whose contributor ids "mine" means: the signed-in person; a lecturer or administrator may name a student of this team."""
    if student is None or account.role is UserRole.STUDENT:
        return account.user.email
    try:
        wanted = uuid.UUID(student)
    except ValueError:
        raise not_found("Student not found") from None
    member = next((m for m in group.members if m.user_id == wanted and m.role is MemberRole.MEMBER), None)
    if member is None:
        raise not_found("Student not found")
    return member.user.email


def my_contributor_ids(reader: ResultsReader, group: Group, run_id: str, account: Account, student: str | None) -> list[str]:
    return reader.contributor_ids(group.code, run_id, viewer_email(group, account, student))


@router.get("/teams/{team}/runs", summary="The Security Assistant runs of a team")
def list_runs(team: str, account: Onboarded, db: Db, reader: Reader) -> dict:
    group = team_access(db, team, account)
    return {"demo_data": demo_data(), "team": group.code, "team_repo_url": group.repo_url, "runs": reader.summaries(group.code)}


@router.get("/teams/{team}/students", summary="The students of a team (lecturers and admins)")
def list_students(team: str, account: StaffOnly, db: Db) -> list[dict]:
    group = team_access(db, team, account)
    return [{"id": str(m.user_id), "display_name": m.user.name, "github_username": m.user.github_username} for m in rules.students(group)]


@router.get("/teams/{team}/runs/{run}", summary="One run: provenance, stages, tool runs, coverage and counts")
def read_run(team: str, run: str, account: Onboarded, db: Db, reader: Reader, student: Annotated[str | None, Query()] = None) -> dict:
    group = team_access(db, team, account)
    data = load_run(reader, group, run)
    rep, usage = data["report"], data["report"].get("llm_usage") or {}
    meta = rep["meta"]
    return {
        "run_id": run, "demo_data": demo_data(), "team": group.code, "team_repo_url": group.repo_url,
        "manifest": data["manifest"],
        "stages": rep["run"]["stages"],
        "run": {"complete": rep["run"]["complete"], "incomplete_reasons": rep["run"]["incomplete_reasons"], "llm_refused": rep["run"].get("llm_refused", False)},
        "scan": rep["scan"],
        "counts": counts(rep["findings"]),
        "llm": {"model": meta.get("llm_model"), "temperature": meta.get("temperature"), "seed": usage.get("seed"),
                "interpreter_prompt": meta.get("interpreter_prompt"), "trace_prompt": meta.get("trace_prompt"), "risk_version": meta.get("risk_version"),
                "threshold": meta.get("threshold"), "total_tokens": usage.get("total_tokens"), "tutor_is_mock": bool((rep.get("questions") or {}).get("meta", {}).get("tutor_is_mock", True))},
        "my_contributor_ids": my_contributor_ids(reader, group, run, account, student),
    }


# ---- findings ---------------------------------------------------------------------------------------------------------------------------
HIDDEN_FOR_SECRETS = "Code line hidden for secrets"


def _contributor(finding: dict) -> str | None:
    return (finding.get("introducing_commit") or {}).get("contributor")


def _summary(f: dict, mine: set[str]) -> dict:
    risk = f.get("risk") or {}
    return {
        "group_id": f["group_id"], "category": f["category"], "title": (f.get("message") or f["rule_id"])[:160], "tool": f["tool"], "rule_id": f["rule_id"],
        "cwe": f.get("cwe"), "file_path": f.get("file_path"), "line": f.get("line"), "package": f.get("package"),
        "status": f["status"], "confidence": f.get("confidence"), "risk_rank": risk.get("rank"), "risk_score": risk.get("score"),
        "contributor": _contributor(f), "mine": bool(_contributor(f) and _contributor(f) in mine),
        "links": [{"kind": x["kind"], "id": x["id"], "status": x["status"]} for x in f.get("links") or []],
        "probe_decision": (f.get("probe") or {}).get("decision"),
    }


def _card(f: dict, mine: set[str]) -> dict:
    """The whole finding. A secret finding never shows its code line: `snippet_note` tells the page what to show instead."""
    card = {**f, "mine": bool(_contributor(f) and _contributor(f) in mine)}
    if f["category"] == "V4":
        card["snippet_note"] = HIDDEN_FOR_SECRETS
    return card


Category = Annotated[str | None, Query(pattern="^V[1-5]$")]
Status = Annotated[str | None, Query(pattern="^(confirmed|dismissed|uncertain|not interpreted)$")]


@router.get("/teams/{team}/runs/{run}/findings", summary="The findings of a run, by category, status and 'mine'")
def list_findings(team: str, run: str, account: Onboarded, db: Db, reader: Reader, category: Category = None, status: Status = None,
                  mine: bool = False, student: Annotated[str | None, Query()] = None) -> dict:
    group = team_access(db, team, account)
    data = load_run(reader, group, run)
    ids = set(my_contributor_ids(reader, group, run, account, student))
    rows = [_summary(f, ids) for f in data["report"]["findings"]]
    rows = [r for r in rows if (category is None or r["category"] == category) and (status is None or r["status"] == status) and (not mine or r["mine"])]
    rows.sort(key=lambda r: (r["risk_rank"] is None, r["risk_rank"] or 0, r["group_id"]))
    return {"run_id": run, "demo_data": demo_data(), "my_contributor_ids": sorted(ids), "counts": counts(data["report"]["findings"]), "findings": rows}


@router.get("/teams/{team}/runs/{run}/findings/{group_id}", summary="One finding with everything the run knows about it")
def read_finding(team: str, run: str, group_id: str, account: Onboarded, db: Db, reader: Reader, student: Annotated[str | None, Query()] = None) -> dict:
    group = team_access(db, team, account)
    data = load_run(reader, group, run)
    found = next((f for f in data["report"]["findings"] if f["group_id"] == group_id), None)
    if found is None:
        raise not_found("Finding not found")
    return _card(found, set(my_contributor_ids(reader, group, run, account, student)))


# ---- learning verification (a mock Tutor), agents, audit, workflow, evidence, compare -----------------------------------------------------
MOCK_TITLE = "comprehension check results (mock)"


def _learning_item(f: dict, mine: set[str]) -> dict:
    p = f["probe"]
    return {"group_id": f["group_id"], "category": f["category"], "title": (f.get("message") or f["rule_id"])[:160], "mine": bool(_contributor(f) and _contributor(f) in mine),
            "concept": (f.get("fix_guidance") or {}).get("title"), "concept_id": (f.get("fix_guidance") or {}).get("id"),
            "question": p.get("question"), "attempts": p.get("attempt_log") or [], "scores": p.get("scores") or [], "threshold": p.get("threshold"),
            "decision": p.get("decision"), "escalation_reason": p.get("escalation_reason")}


def learning_summary(items: list[dict]) -> dict:
    return {"title": MOCK_TITLE, "concepts": len({i["concept_id"] for i in items if i["concept_id"]}),
            "closed": sum(i["decision"] == "closed" for i in items), "escalated": sum(i["decision"] == "escalated" for i in items),
            "open": sum(i["decision"] not in ("closed", "escalated") for i in items), "attempts": sum(len(i["attempts"]) for i in items)}


@router.get("/teams/{team}/runs/{run}/learning", summary="Probe questions and the (mock) Tutor's results")
def read_learning(team: str, run: str, account: Onboarded, db: Db, reader: Reader, mine: bool = False,
                  student: Annotated[str | None, Query()] = None) -> dict:
    group = team_access(db, team, account)
    rep = load_run(reader, group, run)["report"]
    ids = set(my_contributor_ids(reader, group, run, account, student))
    items = [_learning_item(f, ids) for f in rep["findings"] if f.get("probe")]
    shown = [i for i in items if i["mine"]] if mine else items
    qmeta = (rep.get("questions") or {}).get("meta") or {}
    return {"run_id": run, "demo_data": demo_data(), "title": MOCK_TITLE, "threshold": qmeta.get("threshold", (rep["meta"] or {}).get("threshold")),
            "tutor": {"label": qmeta.get("tutor_label"), "is_mock": bool(qmeta.get("tutor_is_mock", True))},
            "my_contributor_ids": sorted(ids), "items": shown, "summary": learning_summary(shown), "summary_all": learning_summary(items)}


@router.get("/teams/{team}/runs/{run}/agents", summary="The decision trails of the three agents and the governance summary")
def read_agents(team: str, run: str, account: Onboarded, db: Db, reader: Reader) -> dict:
    group = team_access(db, team, account)
    rep = load_run(reader, group, run)["report"]
    return {"run_id": run, "demo_data": demo_data(), "decision_trail": rep.get("decision_trail") or {}, "governance": rep.get("governance")}


@router.get("/teams/{team}/runs/{run}/audit", summary="The audit log (hashes and counts only) of a run (lecturers and admins)")
def read_audit(team: str, run: str, account: StaffOnly, db: Db, reader: Reader, limit: Annotated[int, Query(ge=1, le=500)] = 200,
               offset: Annotated[int, Query(ge=0)] = 0) -> dict:
    group = team_access(db, team, account)
    load_run(reader, group, run)
    lines = reader.audit(group.code, run)
    return {"run_id": run, "total": len(lines), "limit": limit, "offset": offset, "lines": lines[offset:offset + limit]}


GRAPHS = ("workflow", "orchestrator", "question", "governance")
_NODE = re.compile(r"^\t([A-Za-z_]\w*)\(")
_EDGE = re.compile(r"^\t([A-Za-z_]\w*) (-->|-\.->) ([A-Za-z_]\w*);")


def parse_mermaid(text: str) -> dict:
    """The nodes and edges of a LangGraph Mermaid export (docs/*.mmd): enough to draw the graph without a Mermaid library."""
    nodes, edges = [], []
    for line in text.splitlines():
        if m := _NODE.match(line):
            nodes.append(m.group(1))
        elif m := _EDGE.match(line):
            edges.append({"from": m.group(1), "to": m.group(3), "conditional": m.group(2) == "-.->"})
    return {"nodes": nodes, "edges": edges}


def graph_status(rep: dict) -> dict:
    """Which nodes ran in this run. Workflow: the stage's own status. The agent graphs: derived from the probes, the scan stage and governance."""
    stages = {s["stage"]: s["status"] for s in rep["run"]["stages"]}
    stages["report"] = "completed"
    gov = rep.get("governance") or {}
    scrutiny = gov.get("scrutiny") or {}
    probes = [f["probe"] for f in rep["findings"] if f.get("probe")]
    asked = [p for p in probes if p.get("attempts")]
    ran, none = "ran", "not run"
    checked, blocked = gov.get("calls_checked", 0) or 0, gov.get("calls_blocked", 0) or 0
    return {
        "workflow": stages,
        "orchestrator": {n: ran if stages.get("scan") in ("completed", "partial") else none for n in ("plan", "execute_action", "update_state", "stop")},
        "question": {"ask": ran if asked else none, "score": ran if asked else none,
                     "follow_up": ran if any(p["attempts"] > 1 for p in asked) else none,
                     "close": ran if any(p.get("decision") == "closed" for p in probes) else none,
                     "escalate": ran if any(p.get("decision") == "escalated" for p in probes) else none},
        "governance": {"check_input": ran if (checked or stages.get("governance") == "completed") else none,
                       "allow": ran if checked > blocked else none, "block": ran if blocked else none,
                       "raise_scrutiny": ran if scrutiny.get("level") not in (None, "normal") else none,
                       "escalate": ran if scrutiny.get("escalated") else none},
    }


@router.get("/teams/{team}/runs/{run}/workflow", summary="The workflow and agent graphs with the nodes that ran highlighted")
def read_workflow(team: str, run: str, account: Onboarded, db: Db, reader: Reader) -> dict:
    group = team_access(db, team, account)
    rep = load_run(reader, group, run)["report"]
    graphs = {}
    for name in GRAPHS:
        try:
            text = reader.shared(f"{name}.mmd")
        except NotFound:
            graphs[name] = {"nodes": [], "edges": [], "mmd": None}
            continue
        graphs[name] = {**parse_mermaid(text), "mmd": text}
    return {"run_id": run, "demo_data": demo_data(), "graphs": graphs, "ran": graph_status(rep)}


MOCKED = [
    {"part": "Tutor and the comprehension score", "status": "mock", "note": "No student answers anything; the scores only demonstrate the flow."},
    {"part": "Requirements and sprint tasks", "status": "local files", "note": "Read from local JSON files; the Requirements agent does not exist."},
    {"part": "LLM policy for the three agents", "status": "not built", "note": "Only deterministic rule policies; the interface is ready."},
    {"part": "Orchestrator wiring, database persistence, webhook to assessment", "status": "not built", "note": "The assessment runs from the command line."},
    {"part": "Checkpointing and resuming a run", "status": "not built", "note": "By design."},
    {"part": "Real CodeQL per-language and OSV fallbacks", "status": "tested with fake tools", "note": "Not exercised against the real tools in this workflow."},
    {"part": "RQ1 on all four demo repositories with one model", "status": "pending", "note": "Needs the model's daily quota; the table is from the saved runs."},
]
STATUS_KEYS = ("confirmed", "dismissed", "uncertain", "not interpreted")


def rq1_rows(reader: ResultsReader) -> list[dict]:
    try:
        text = reader.shared("rq1_comparison.csv")
    except NotFound:
        return []
    return list(csv.DictReader(io.StringIO(text)))


def run_counts(reader: ResultsReader, group: Group) -> list[dict]:
    """Scanner only (every finding group the tools reported) against scanner plus LLM (what the LLM confirmed, dismissed or left open)."""
    rows = []
    for s in reader.summaries(group.code):
        total = {k: sum(row[k] for row in s["counts"].values()) for k in STATUS_KEYS}
        rows.append({"run_id": s["run_id"], "repo": s["repo"], "started_at": s["started_at"], "scanner_findings": sum(total.values()),
                     "confirmed": total["confirmed"], "dismissed": total["dismissed"], "uncertain": total["uncertain"], "not_interpreted": total["not interpreted"]})
    return rows


@router.get("/teams/{team}/evidence", summary="Evidence for the panel: scanner only against scanner plus LLM, RQ1, limitations")
def read_evidence(team: str, account: Onboarded, db: Db, reader: Reader, run: Annotated[str | None, Query()] = None) -> dict:
    group = team_access(db, team, account)
    limitations = load_run(reader, group, run)["report"].get("limitations", []) if run else []
    return {"demo_data": demo_data(), "runs": run_counts(reader, group), "rq1_rows": rq1_rows(reader), "limitations": limitations, "mocked": MOCKED}


def finding_key(f: dict) -> tuple:
    return (f["category"], f["rule_id"], f.get("file_path"), f.get("package"), f.get("line"))


def compare_runs(a: list[dict], b: list[dict]) -> dict:
    """What changed from run a to run b, matching findings on category, rule, file, package and line."""
    old, new = {finding_key(f): f for f in a}, {finding_key(f): f for f in b}

    def brief(f: dict) -> dict:
        return {"category": f["category"], "rule_id": f["rule_id"], "file_path": f.get("file_path"), "line": f.get("line"), "package": f.get("package"),
                "status": f["status"], "group_id": f["group_id"]}

    return {"added": [brief(new[k]) for k in new if k not in old], "removed": [brief(old[k]) for k in old if k not in new],
            "changed": [{**brief(new[k]), "from": old[k]["status"], "to": new[k]["status"]} for k in new if k in old and old[k]["status"] != new[k]["status"]],
            "unchanged_count": sum(1 for k in new if k in old and old[k]["status"] == new[k]["status"])}


@router.get("/teams/{team}/compare", summary="What changed between two runs of the same repository")
def compare(team: str, account: Onboarded, db: Db, reader: Reader, a: str, b: str) -> dict:
    group = team_access(db, team, account)
    run_a, run_b = load_run(reader, group, a), load_run(reader, group, b)
    repo_a = run_a["manifest"].get("repo") or run_a["report"]["meta"].get("source")
    repo_b = run_b["manifest"].get("repo") or run_b["report"]["meta"].get("source")
    if repo_a != repo_b:
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, "different_repositories", "The two runs scanned different repositories")
    return {"a": a, "b": b, "repo": repo_a, "demo_data": demo_data(), **compare_runs(run_a["report"]["findings"], run_b["report"]["findings"])}
