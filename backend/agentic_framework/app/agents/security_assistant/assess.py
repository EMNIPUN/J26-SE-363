"""End to end: fetch, scan, interpret, trace, risk, guidance, questions -> one report.json and one report.md.

    python -m app.agents.security_assistant.assess <https://github.com/owner/repo | local folder> [options]

    --requirements FILE      stories (see traceability.py); without it findings link to commits only
    --tasks FILE             sprint tasks
    --skip codeql,zizmor     do not run these tools (recorded as a coverage gap, so the run is incomplete)
    --reuse-scan FILE        use a saved findings.json instead of scanning (the repo is still fetched for code context)
    --allow-external-llm     required for the LLM stages (interpret, link proposals): without it nothing is sent to any LLM,
                             those stages are skipped and the run is incomplete
    --threshold T            comprehension threshold for the (mock) Tutor, default 0.7
    --ref SHA / --max-findings N / --delay S / --retries N / --out DIR

Every stage is recorded as completed, partial, failed or skipped. Anything but "completed" makes the run INCOMPLETE and says
why; a run is never reported as clean because a stage did not happen. Stages whose input is missing are skipped, not guessed.

Exit code: 0 complete, 2 incomplete, 3 usage error, 4 the LLM stages were refused (no --allow-external-llm).
"""

import argparse
import asyncio
import contextlib
import json
import sys
import time
from pathlib import Path

from app.agents.security_assistant import guidance as guide
from app.agents.security_assistant import interpret as interp
from app.agents.security_assistant import questions as qs
from app.agents.security_assistant import risk as rk
from app.agents.security_assistant import trace as tr
from app.agents.security_assistant import governance as gv
from app.agents.security_assistant.agent_loop import render_trail
from app.agents.security_assistant import orchestrator as orch
from app.agents.security_assistant.dedupe import dedupe
from app.agents.security_assistant.graphs.assess_graph import RunContext, build_assess_graph
from app.agents.security_assistant.interpreter.llm import LLMClient, LLMError, get_default_client
from app.agents.security_assistant.interpreter.models import finding_key
from app.agents.security_assistant.interpreter.redaction import redact_text
from app.agents.security_assistant.pii import PIIRedactor
from app.agents.security_assistant.pipeline import FetchError, fetch_repo
from app.agents.security_assistant.report import (
    build_report, from_json, render_markdown,
)
from app.agents.security_assistant.scan import parse_skip
from app.agents.security_assistant.tools.coverage_gaps import find_dependency_gaps
from app.agents.security_assistant.tools.runner import InvalidRepoPath, default_tools, run_all
from app.agents.security_assistant.traceability import FormatError, Pseudonymizer, load_stories, load_tasks

REPORT_VERSION = "assessment-v1"
STAGES = ("fetch", "scan", "governance", "interpret", "trace", "risk", "guidance", "questions")
NEEDS = {"scan": "fetch", "governance": "scan", "interpret": "governance", "trace": "interpret", "risk": "interpret", "guidance": "scan",
         "questions": "interpret"}
OK = ("completed",)


class Stages:
    """Records what happened to each stage, in order."""

    def __init__(self, say=lambda text: None, items: dict[str, dict] | None = None):
        self.items: dict[str, dict] = items if items is not None else {}  # the run's graph state holds these (graphs/assess_graph.py)
        self._say = say

    def record(self, name: str, status: str, detail: str = "", started: float | None = None) -> None:
        self.items[name] = {"stage": name, "status": status, "detail": detail,
                            "seconds": round(time.monotonic() - started, 2) if started is not None else 0.0}
        self._say(f"[{name}] {status}" + (f": {detail}" if detail else ""))

    def usable(self, name: str) -> bool:
        """A stage's output can be used if it ran, even partly."""
        return self.items.get(name, {}).get("status") in ("completed", "partial")

    def blocked_by(self, name: str) -> str | None:
        need = NEEDS.get(name)
        return need if need and not self.usable(need) else None

    def skip(self, name: str, why: str) -> None:
        self.record(name, "skipped", why)


def _label(source: str, is_url: bool) -> str:
    return source if is_url else Path(source).name or "local folder"


def _limitations(scan: dict, idoc: dict | None, qdoc: dict | None, reused: bool, has_requirements: bool) -> list[str]:
    L = ["The report lists scanner findings and the LLM's opinion of them. The LLM can be wrong; 'dismissed' is an argument "
         "for a false positive, not proof. No student code was executed, so nothing was confirmed by running an exploit.",
         "Scanner coverage is limited to what the tools support. A category with 0 findings only means something when its "
         "coverage is FULL (see the coverage table)."]
    if scan["skipped_tools"]:
        L.append(f"Skipped tools (not run): {', '.join(scan['skipped_tools'])}. Findings these tools would have reported are missing.")
    L += [f"Tool limitation: {w}" for w in scan["warnings"]]
    if reused:
        L.append("The scan was reused from a saved findings.json: line numbers and commit ids refer to the repository that was scanned then (a "
                 "history lookup finds nothing if they do not exist in the fetched copy), and the coverage table describes that earlier run.")
    if idoc is not None and idoc["summary"]["not_analysed_findings"]:
        L.append(f"{idoc['summary']['not_analysed_findings']} finding(s) were not analysed by the LLM (call limit or failed stage).")
    if not has_requirements:
        L.append("No requirements or sprint-task file was given, so findings are linked to commits only, not to stories or tasks.")
    L.append("Requirements and tasks come from local files, not from the Requirements agent; a link is 'verified' only when a "
             "simple rule supports it (commit message or task names the id, or the file/endpoint appears in one story/task).")
    L.append("The 'introducing commit' is the commit that added the line. It shows where the code came from, not who is at fault.")
    L.append("The risk score is a rule-based ranking with weights chosen by the developers; it is not a measured probability and "
             "it does not know whether a vulnerable dependency's code is actually called.")
    if qdoc is not None and qdoc["meta"]["tutor_is_mock"]:
        L.append("The Tutor is a MOCK: no student was asked and no answer was graded. The comprehension scores and the "
                 "closed/open decisions are simulated and only demonstrate the flow.")
    L.append("A probe question is built from the flagged function with simple extraction (Python ast; text search for Java and "
             "JS/TS); it can pick the wrong function in unusual code.")
    L.append("Only https://github.com repositories can be fetched. Gradle dependencies are only read with a gradle.lockfile; "
             "Maven transitive dependencies need the registry to be reachable.")
    return L


def _overview(findings: list[dict]) -> str:
    def cell(t) -> str:
        return " ".join(str(t).split()).replace("|", "\\|")

    M = ["## Findings overview", "",
         "| rank | group | finding | where | status | conf. | evidence | introducing commit | links | risk | probe question |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    order = sorted(findings, key=lambda f: (f["risk"]["rank"] if f["risk"] else 10 ** 6, f["group_id"]))
    for f in order:
        where = (f["file_path"] or f["package"] or "-") + (f":{f['line']}" if f["line"] else "")
        c = f["introducing_commit"]
        links = ", ".join(f"{l['id']} ({l['status']})" for l in f["links"]) or "-"
        q = f["probe"]
        probe = (f"{q['decision']} after {q['attempts']} question(s) (last score {q['tutor']['score']:.2f}, MOCK)"
                 if q and q["attempts"] else f"{q['decision']} (not asked)") if q else "-"
        M.append(f"| {f['risk']['rank'] if f['risk'] else '-'} | {f['group_id']} | {f['category']} {cell(f['rule_id'])} | {cell(where)} | "
                 f"**{f['status']}** | {f['confidence'] if f['confidence'] is not None else '-'} | {cell(', '.join(f['evidence_ids']) or '-')} | "
                 f"{('`' + c['sha'][:7] + '` ' + c['contributor']) if c else '-'} | {cell(links)} | "
                 f"{('%.1f' % f['risk']['score']) if f['risk'] else '-'} | {probe} |")
    return "\n".join(M) + "\n"


def _stage_table(stages: list[dict]) -> str:
    M = ["## Stages", "", "| stage | status | detail |", "|---|---|---|"]
    M += [f"| {s['stage']} | **{s['status']}** | {' '.join(s['detail'].split()).replace('|', chr(92) + '|') or '-'} |" for s in stages]
    return "\n".join(M) + "\n"


def render(report: dict, scan_md: str, idoc, tdoc, risk_doc, qdoc, findings: list[dict]) -> str:
    run = report["run"]
    banner = ("> **INCOMPLETE RUN.** This is not a clean result.\n" + "\n".join(f"> - {r}" for r in run["incomplete_reasons"])
              if not run["complete"] else "> All stages completed. Read the limitations below before relying on the result.")
    M = [f"# Security Assistant report: {report['meta']['source']}", "", banner, "", _stage_table(run["stages"])]
    u = report.get("llm_usage") or {}
    if u.get("total_tokens"):
        M.append(f"LLM usage: {u['total_tokens']} tokens ({u['interpret']['calls']} interpretation call(s), "
                 f"{u['link_proposals']['calls']} link proposal(s)), model {u['model']}.\n")
    if findings:
        M.append(_overview(findings))
    M.append(scan_md)
    if idoc is not None:
        M.append(interp.render_section(idoc))
    if tdoc is not None:
        M.append(tr.render_section(tdoc))
    if risk_doc is not None:
        M.append(rk.render_section(risk_doc))
    if qdoc is not None:
        M.append(qs.render_section(qdoc))
    if report.get("governance"):
        M.append(gv.render_section(report["governance"]))
    M.append(render_trail(report.get("decision_trail") or {}))
    M += ["## Limitations", ""] + [f"- {x}" for x in report["limitations"]]
    return "\n".join(M) + "\n"


async def run_pipeline(repo_url: str, requirements_file: Path | str | None = None, sprint_tasks_file: Path | str | None = None,
                       skip: list[str] | None = None, reuse_scan: Path | str | None = None, *,
                       out_dir: Path | str | None = None, allow_external_llm: bool = False, client: LLMClient | None = None,
                       tutor: qs.TutorChannel | None = None, threshold: float | None = None, ref: str | None = None,
                       tools=None, max_findings: int | None = None, delay: float = 0.0, retries: int = 2,
                       governance_warn_only: bool = False, fetch_options: dict | None = None, agent_config=None, orchestrator_policy=None, question_config=None, question_policy=None, say=lambda text: None) -> dict:
    """Run every stage and write report.json and report.md into `out_dir`. Returns the report (a dict).
    Raises ValueError for unusable arguments (an unknown tool in `skip`, a threshold outside 0..1)."""
    skipped = parse_skip(skip)
    threshold = qs.threshold_from_env() if threshold is None else threshold
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("the comprehension threshold must be between 0 and 1")
    is_url = str(repo_url).startswith(("https://", "http://"))
    label = _label(str(repo_url), is_url)
    out = Path(out_dir) if out_dir else Path("scan_output") / f"assessment_{label}"
    out.mkdir(parents=True, exist_ok=True)
    pii = PIIRedactor.from_env()  # one redactor for the whole run: the same placeholders in the report snippets, prompts and questions
    gov = gv.Governance(out, warn_only=governance_warn_only, pii=pii)
    gov.start(command="assess", prompt_version=interp.PROMPT_VERSION, link_prompt_version=tr.TRACE_PROMPT_VERSION)
    stack = contextlib.AsyncExitStack()
    ctx = RunContext(repo_url=str(repo_url), requirements_file=requirements_file, sprint_tasks_file=sprint_tasks_file, reuse_scan=reuse_scan,
                     out=out, allow_external_llm=allow_external_llm, client=client, tutor=tutor, threshold=threshold, ref=ref, tools=tools,
                     max_findings=max_findings, delay=delay, retries=retries, fetch_options=fetch_options, agent_config=agent_config,
                     orchestrator_policy=orchestrator_policy, question_config=question_config, question_policy=question_policy, say=say,
                     label=label, is_url=is_url, gov=gov, pii=pii, stack=stack, skip=skipped)
    try:
        # the whole flow is one LangGraph workflow (graphs/assess_graph.py); a fetched checkout is deleted when the stack closes, after the report
        final = await build_assess_graph(ctx).ainvoke({"stages": {}, "trails": {}}, {"recursion_limit": 40})
    finally:
        await stack.aclose()
    return final["report"]


def _usage(idoc, link_usage: dict) -> dict:
    """Tokens the run used: interpreter calls (from their call records) and link proposals."""
    calls = [g["result"]["call"] for g in (idoc["groups"] if idoc else []) if g["result"].get("call")]
    interpret = {"calls": len(calls), "prompt_tokens": sum(c.get("prompt_tokens") or 0 for c in calls),
                 "completion_tokens": sum(c.get("completion_tokens") or 0 for c in calls)}
    links = {"calls": link_usage.get("calls", 0), "prompt_tokens": link_usage.get("prompt_tokens", 0),
             "completion_tokens": link_usage.get("completion_tokens", 0)}
    total = sum(x["prompt_tokens"] + x["completion_tokens"] for x in (interpret, links))
    return {"interpret": interpret, "link_proposals": links, "total_tokens": total, "model": idoc["meta"]["model"] if idoc else None,
            "seed": next((c.get("seed") for c in calls if c.get("seed") is not None), None)}


def _collect(result, idoc, tdoc, risk_doc, qdoc) -> list[dict]:
    """One record per finding group with everything the stages produced for it."""
    if result is None:
        return []
    traces = {t["group_id"]: t for t in (tdoc["traces"] if tdoc else [])}
    ranked = {e["group_id"]: e for e in (risk_doc["ranked"] if risk_doc else [])}
    probes = {i["question"]["group_id"]: i for i in (qdoc["questions"] if qdoc else [])}
    if idoc is not None:
        source = [(g["group_id"], g["kind"], g["package"], g["representative"], len(g["members"]), g["result"]) for g in idoc["groups"]]
    else:  # not interpreted: the scanner findings, grouped as the interpreter would have grouped them
        source = [(g.id, g.kind, g.package, interp._brief(g.representative), len(g.members), None) for g in dedupe(result.findings)[0]]
    out = []
    for gid, kind, package, rep, members, res in source:
        g = guide.by_id(rep.get("fix_pattern"))
        t, r, p = traces.get(gid), ranked.get(gid), probes.get(gid)
        out.append({
            "group_id": gid, "kind": kind, "package": package, "category": rep["category"], "rule_id": rep["rule_id"],
            "tool": rep["tool"], "file_path": rep["file_path"], "line": rep["line"], "severity_tool": rep["severity_tool"],
            "findings_in_group": members,
            "status": res["status"] if res else "not interpreted", "confidence": res["confidence"] if res else None,
            "rationale": (res["error"] or res["downgrade_reason"] or res["rationale"]) if res else "",
            "evidence_ids": res["evidence_ids"] if res else [],
            "recommendation": res["recommendation"] if res else "",
            "introducing_commit": t["introducing_commit"] if t else None, "links": t["links"] if t else [],
            "rejected_links": t["rejected_links"] if t else [], "trace_notes": t["notes"] if t else [],
            "risk": {"rank": r["rank"], "score": r["score"], "breakdown": r["factors"]} if r else None,
            "fix_guidance": {"id": g.id, "title": g.title, "steps": list(g.steps)} if g else None,
            "probe": {"question": p["question"]["text"], "code": p["question"]["code"], "decision": p["decision"],
                      "attempts": len(p["attempts"]), "scores": [a["score"] for a in p["attempts"]],
                      "escalation_reason": p.get("escalation_reason"),
                      "threshold": p["threshold"], "tutor": p["tutor_result"]} if p else None,
        })
    return out


# ---- command line -------------------------------------------------------------------------------------------------------------
async def main(argv: list[str] | None = None, client: LLMClient | None = None, tutor=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("--requirements", type=Path)
    ap.add_argument("--tasks", type=Path)
    ap.add_argument("--skip", action="append", metavar="TOOLS")
    ap.add_argument("--reuse-scan", type=Path, dest="reuse_scan")
    ap.add_argument("--allow-external-llm", action="store_true")
    ap.add_argument("--governance-warn-only", action="store_true",
                    help="a failed secret or personal-data check before a call is recorded but does not block it (off by default)")
    ap.add_argument("--threshold", type=float)
    ap.add_argument("--ref")
    ap.add_argument("--max-findings", type=int)
    ap.add_argument("--delay", type=float, default=0.0)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    if not args.allow_external_llm:
        print("note: --allow-external-llm not given: the LLM stages (interpret, trace, risk, questions) will be skipped and "
              "the run will be incomplete.\n" + interp.NOTICE, file=sys.stderr)
    try:
        report = await run_pipeline(args.source, args.requirements, args.tasks, parse_skip(args.skip), args.reuse_scan,
                                    out_dir=args.out, allow_external_llm=args.allow_external_llm, client=client, tutor=tutor,
                                    threshold=args.threshold, ref=args.ref, max_findings=args.max_findings, delay=args.delay,
                                    retries=args.retries, governance_warn_only=args.governance_warn_only, say=print)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 3
    out = args.out or Path("scan_output") / f"assessment_{_label(args.source, args.source.startswith('http'))}"
    if report["llm_usage"]["total_tokens"]:
        print(f"LLM tokens used: {report['llm_usage']['total_tokens']}")
    print(("COMPLETE" if report["run"]["complete"] else "INCOMPLETE") + f" - wrote {out / 'report.json'} and {out / 'report.md'}")
    for r in report["run"]["incomplete_reasons"]:
        print(f"  - {r}")
    if report["run"]["llm_refused"]:
        return 4
    return 0 if report["run"]["complete"] else 2


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    sys.exit(asyncio.run(main()))
