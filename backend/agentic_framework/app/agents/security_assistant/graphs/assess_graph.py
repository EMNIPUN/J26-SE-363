"""The whole Security Assistant flow as one LangGraph workflow.

    START -> fetch -+-> scan -+-> governance -> interpret -> trace -> risk -> guidance -> questions -> report -> END
                    |         |
                    +---------+--> report            (nothing was fetched / no scan result: nothing downstream can run)

fetch        clones (or opens) the repository; names in its git history become known names for the redactor.
scan         the Analysis Orchestrator agent (graphs/orchestrator_graph.py) runs the tools, or reviews a reused scan.
governance   the governance gate before anything is sent: tool allow-list, repository scan for injection indicators (the stateful gate,
             graphs/governance_graph.py, raises its scrutiny from them), the secret values to look for. It stays in the loop for every LLM call.
interpret    the LLM judges each finding (every call passes the governance gate).
trace        introducing commit and requirement links (link proposals pass the gate too).
risk         rule-based ranking.
guidance     the standard fix advice per type of issue.
questions    the Question agent (graphs/question_graph.py) per confirmed finding, with the mock Tutor.
report       fills in the stages that did not run ("skipped, needs X"), marks the run INCOMPLETE with every reason, scans the report for leaked
             values, writes report.json, report.md and audit.jsonl.

The stage statuses live in the graph state (`stages`) and are the single source for the report. A failed or partial stage is never hidden: the
edges leave the chain only where nothing downstream could run (fetch or scan unusable) and then go straight to the report node; everywhere
else the next stage runs or records that it was skipped and why. Every path ends in the report node. No checkpointing, no persistence.
"""

import contextlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

NODES = ("fetch", "scan", "governance", "interpret", "trace", "risk", "guidance", "questions", "report")


def _merge(old: dict | None, new: dict | None) -> dict:
    return {**(old or {}), **(new or {})}


class AssessState(TypedDict, total=False):
    stages: Annotated[dict, _merge]  # stage name -> {"stage", "status", "detail", "seconds"}: the statuses of the run
    trails: Annotated[dict, _merge]  # component -> decision trail
    repo: Any
    result: Any
    scan_report: Any
    scan_md: str
    skipped: list
    reused: bool
    plan: Any
    llm: Any
    idoc: dict | None
    tdoc: dict | None
    risk_doc: dict | None
    qdoc: dict | None
    guidance_used: dict
    llm_refused: bool
    report: dict


@dataclass
class RunContext:
    """The inputs of one run and the objects that live for the whole run. The nodes read them; none of them is a stage result."""

    repo_url: str
    requirements_file: Any
    sprint_tasks_file: Any
    reuse_scan: Any
    out: Path
    allow_external_llm: bool
    client: Any
    tutor: Any
    threshold: float
    ref: str | None
    tools: Any
    max_findings: int | None
    delay: float
    retries: int
    fetch_options: dict | None
    agent_config: Any
    orchestrator_policy: Any
    question_config: Any
    question_policy: Any
    say: Any
    label: str
    is_url: bool
    gov: Any
    pii: Any
    stack: contextlib.AsyncExitStack
    skip: list = field(default_factory=list)
    link_usage: dict = field(default_factory=dict)
    t0: float = field(default_factory=time.monotonic)


def build_assess_graph(ctx: RunContext):
    # imported here: assess.py imports this module, and the nodes use its helpers and stage vocabulary
    from app.agents.security_assistant import assess as A
    from app.agents.security_assistant import governance as gv
    from app.agents.security_assistant import guidance as guide
    from app.agents.security_assistant import interpret as interp
    from app.agents.security_assistant import manifest
    from app.agents.security_assistant import orchestrator as orch
    from app.agents.security_assistant import questions as qs
    from app.agents.security_assistant import risk as rk
    from app.agents.security_assistant import trace as tr
    from app.agents.security_assistant.interpreter.llm import get_default_client
    from app.agents.security_assistant.interpreter.redaction import redact_text
    from app.agents.security_assistant.pipeline import FetchError, fetch_repo
    from app.agents.security_assistant.report import build_report, from_json, render_markdown
    from app.agents.security_assistant.tools.coverage_gaps import find_dependency_gaps
    from app.agents.security_assistant.tools.runner import InvalidRepoPath, default_tools
    from app.agents.security_assistant.traceability import FormatError, Pseudonymizer, load_stories, load_tasks

    gov, pii, out = ctx.gov, ctx.pii, ctx.out

    def stages_of(state: AssessState) -> "A.Stages":
        return A.Stages(ctx.say, dict(state.get("stages") or {}))

    def failed(exc: Exception) -> str:
        return f"{type(exc).__name__}: {redact_text(str(exc))[:160]}"

    # ---- fetch ---------------------------------------------------------------------------------------------------------------------------
    async def fetch(state: AssessState) -> dict:
        st = stages_of(state)
        try:
            opened = fetch_repo(str(ctx.repo_url), ctx.ref, **(ctx.fetch_options or {})) if ctx.is_url else contextlib.nullcontext(Path(ctx.repo_url))
            repo = Path(await ctx.stack.enter_async_context(opened))
            if not repo.is_dir():
                raise InvalidRepoPath(f"not a directory: {ctx.repo_url}")
            pii.learn_git_names(repo)  # names of the git history are known names for every later stage
            st.record("fetch", "completed", "repository fetched" if ctx.is_url else "local folder", ctx.t0)
        except (FetchError, InvalidRepoPath, OSError) as exc:
            repo = None
            st.record("fetch", "failed", redact_text(str(exc))[:200], ctx.t0)
        return {"stages": st.items, "repo": repo}

    def after_fetch(state: AssessState) -> str:
        return "scan" if state.get("repo") is not None else "report"  # nothing fetched: nothing downstream can run

    # ---- scan (nests the Analysis Orchestrator graph) ----------------------------------------------------------------------------------------
    async def scan(state: AssessState) -> dict:
        st, repo = stages_of(state), state["repo"]
        t = time.monotonic()
        skipped, reused, trails, result, scan_report, scan_md = list(ctx.skip), False, {}, None, None, ""
        try:
            if ctx.reuse_scan:
                result, saved_skips = from_json(Path(ctx.reuse_scan).read_text(encoding="utf-8"))
                skipped = sorted(set(skipped) | set(saved_skips))
                reused = True
                detail = f"reused saved findings ({Path(ctx.reuse_scan).name}); nothing was scanned now"
            else:
                chosen = [x for x in (ctx.tools if ctx.tools is not None else default_tools()) if x.name not in skipped]
                if (rejected := gov.check_tools([x.name for x in chosen], "tools to run")):
                    raise gv.ToolNotAllowed(f"governance: tool(s) not on the allow-list: {', '.join(rejected)}")
                outcome = await orch.orchestrate(repo, chosen, config=ctx.agent_config, audit=gov.audit, skipped=skipped, policy=ctx.orchestrator_policy)
                result, trails["Analysis Orchestrator"] = outcome.result, outcome.trail
                detail = (f"{len(result.runs)} tool run(s), {len(result.findings)} finding(s); agent loop: {outcome.steps} step(s), "
                          f"{outcome.stop_reason}")
            if reused and (rejected := gov.check_tools([r.tool for r in result.runs] + [f.tool for f in result.findings], "the reused findings.json")):
                raise gv.ToolNotAllowed(f"governance rejected the reused findings.json: tool(s) not on the allow-list: {', '.join(rejected)}")
            if reused and not result.coverage_gaps and "coverage_gaps" not in json.loads(Path(ctx.reuse_scan).read_text(encoding="utf-8"))["scan"]:
                result.coverage_gaps = find_dependency_gaps(repo)  # a findings.json from before this check: look at the repo now
            if reused:  # the same loop in review mode: no tool can run, but gaps and holes are decided on and shown
                outcome = await orch.review(result, config=ctx.agent_config, audit=gov.audit, skipped=skipped, policy=ctx.orchestrator_policy)
                result, trails["Analysis Orchestrator"] = outcome.result, outcome.trail
                detail += f"; agent loop (review, no tool can run): {outcome.steps} step(s), {outcome.stop_reason}"
            scan_report = build_report(result, skipped=skipped, source=ctx.label, repo=repo, pii=pii)
            scan_report.commit_sha = ctx.ref if ctx.is_url else scan_report.commit_sha
            scan_md = render_markdown(scan_report)
            bad = [r.tool for r in result.runs if r.status.value not in ("succeeded", "not_applicable")]
            st.record("scan", "partial" if bad else "completed", detail + (f"; did not finish: {', '.join(bad)}" if bad else ""), t)
        except Exception as exc:  # a stage must never take the whole run down silently
            result = scan_report = None
            st.record("scan", "failed", failed(exc), t)
        return {"stages": st.items, "trails": trails, "result": result, "scan_report": scan_report, "scan_md": scan_md, "skipped": skipped,
                "reused": reused}

    def after_scan(state: AssessState) -> str:
        return "governance" if state.get("result") is not None else "report"  # no scan result: nothing downstream can run

    # ---- governance --------------------------------------------------------------------------------------------------------------------------
    def governance(state: AssessState) -> dict:
        st = stages_of(state)
        if (why := st.blocked_by("governance")):
            st.skip("governance", f"needs {why}")
        else:
            t = time.monotonic()
            try:
                gov.set_secret_values(gv.known_secret_values(state["repo"], state["result"].findings))
                hits = gov.scan_repo(state["repo"])  # the stateful gate (graphs/governance_graph.py) raises its scrutiny from the indicators
                st.record("governance", "completed",
                          f"{'WARN-ONLY mode' if gov.warn_only else 'enforcing'}; tool allow-list ok; {gov.repo_files_scanned} README/commit message(s) "
                          f"scanned, {len(hits)} prompt-injection indicator(s) logged (an indicator, not proof)", t)
            except Exception as exc:
                st.record("governance", "failed", failed(exc), t)
        return {"stages": st.items}

    # ---- interpret ---------------------------------------------------------------------------------------------------------------------------
    async def interpret(state: AssessState) -> dict:
        st = stages_of(state)
        upd: dict = {"idoc": None, "plan": None, "llm": None, "llm_refused": False}
        if (why := st.blocked_by("interpret")):
            st.skip("interpret", f"needs {why}")
        elif not ctx.allow_external_llm:
            upd["llm_refused"] = True
            st.skip("interpret", "--allow-external-llm was not given: nothing was sent to any LLM")
        else:
            t = time.monotonic()
            try:
                plan = interp.make_plan(state["result"], state["repo"], max_findings=ctx.max_findings, pii=pii)
                llm = ctx.client or get_default_client(retries=ctx.retries, backoff=max(0.5, ctx.delay))
                upd["plan"], upd["llm"] = plan, llm
                outcomes = await interp.run_calls(plan, llm, delay=ctx.delay, say=lambda text: None, governance=gov)
                idoc = interp.to_document(plan, outcomes, llm.model, {
                    "findings_file": "(this run)", "delay_s": ctx.delay, "retries": ctx.retries, "max_findings": ctx.max_findings,
                    "only_category": None, "temperature": getattr(llm, "temperature", None)})
                upd["idoc"] = idoc
                s = idoc["summary"]
                bad = s["uncertain_because"]["llm_error"] + s["uncertain_because"]["output_rejected"] + s["uncertain_because"]["governance_blocked"]
                cut = s["not_analysed_findings"]
                st.record("interpret", "partial" if bad or cut else "completed",
                          f"{s['analysed_calls']} call(s): confirmed {s['confirmed']}, dismissed {s['dismissed']}, uncertain "
                          f"{s['uncertain']}" + (f"; {bad} finding(s) with a failed, rejected or governance-blocked call" if bad else "")
                          + (f"; {cut} not analysed" if cut else ""), t)
            except Exception as exc:
                upd["idoc"] = None
                st.record("interpret", "failed", failed(exc), t)
        return {"stages": st.items, **upd}

    # ---- trace -------------------------------------------------------------------------------------------------------------------------------
    async def trace(state: AssessState) -> dict:
        st = stages_of(state)
        tdoc = None
        if (why := st.blocked_by("trace")):
            st.skip("trace", f"needs {why}")
        else:
            t = time.monotonic()
            try:
                stories = load_stories(Path(ctx.requirements_file)) if ctx.requirements_file else []
                tasks = load_tasks(Path(ctx.sprint_tasks_file)) if ctx.sprint_tasks_file else []
                pseudo = Pseudonymizer.load(out / "trace_mapping.local.json")
                plan, llm = state.get("plan"), state.get("llm")
                proposer = (llm or ctx.client or get_default_client(retries=ctx.retries, backoff=max(0.5, ctx.delay))) if (stories or tasks) else None
                traced = await tr.trace_all(state["idoc"], state["repo"], stories, tasks, pseudo, plan.pii if plan else pii, client=proposer,
                                            delay=ctx.delay, usage=ctx.link_usage, governance=gov)
                pseudo.save(out / "trace_mapping.local.json")
                tdoc = tr.build_document(traced, {
                    "interpreted_file": "(this run)", "requirements_file": Path(ctx.requirements_file).name if ctx.requirements_file else None,
                    "tasks_file": Path(ctx.sprint_tasks_file).name if ctx.sprint_tasks_file else None, "propose_links": bool(stories or tasks),
                    "llm_model": getattr(proposer, "model", None), "prompt_version": tr.TRACE_PROMPT_VERSION})
                s = traced["summary"]
                st.record("trace", "partial" if s["proposal_failures"] else "completed",
                          f"{s['with_introducing_commit']}/{s['confirmed_findings']} with an introducing commit; links "
                          f"{s['verified_links']} verified, {s['candidate_links']} candidate"
                          + ("" if (stories or tasks) else "; no requirements file: commits only"), t)
            except (FormatError, OSError, ValueError) as exc:
                st.record("trace", "failed", failed(exc), t)
            except Exception as exc:
                st.record("trace", "failed", failed(exc), t)
        return {"stages": st.items, "tdoc": tdoc}

    # ---- risk --------------------------------------------------------------------------------------------------------------------------------
    def risk(state: AssessState) -> dict:
        st = stages_of(state)
        risk_doc = None
        if (why := st.blocked_by("risk")):
            st.skip("risk", f"needs {why}")
        else:
            t = time.monotonic()
            try:
                risk_doc = rk.rank(state["idoc"], state["repo"])
                st.record("risk", "completed", f"{len(risk_doc['ranked'])} ranked, {len(risk_doc['excluded'])} dismissed (not ranked)", t)
            except Exception as exc:
                st.record("risk", "failed", failed(exc), t)
        return {"stages": st.items, "risk_doc": risk_doc}

    # ---- guidance (needs only the scanner findings) -----------------------------------------------------------------------------------------------
    def guidance(state: AssessState) -> dict:
        st = stages_of(state)
        used: dict = {}
        if (why := st.blocked_by("guidance")):
            st.skip("guidance", f"needs {why}")
        else:
            t = time.monotonic()
            try:
                for f in state["result"].findings:
                    g = guide.guidance_for(f)
                    used.setdefault(g.id, {"id": g.id, "title": g.title, "why": g.why, "steps": list(g.steps), "references": guide.references(g, f)})
                st.record("guidance", "completed", f"{len(used)} standard fix entr(ies) apply", t)
            except Exception as exc:
                st.record("guidance", "failed", failed(exc), t)
        return {"stages": st.items, "guidance_used": used}

    # ---- questions (nests the Question Agent graph) -----------------------------------------------------------------------------------------------
    async def questions(state: AssessState) -> dict:
        st = stages_of(state)
        qdoc, trails = None, {}
        if (why := st.blocked_by("questions")):
            st.skip("questions", f"needs {why}")
        else:
            t = time.monotonic()
            try:
                plan = state.get("plan")
                qdoc = await qs.generate(state["idoc"], state["repo"], ctx.tutor or qs.MockTutor(), ctx.threshold, plan.pii if plan else pii,
                                         audit=gov.audit, config=ctx.question_config, policy=ctx.question_policy)
                trails["Question Generation"] = qdoc["decision_trail"]
                s = qdoc["summary"]
                st.record("questions", "completed", f"{s['questions']} finding(s): {s['closed']} closed, {s['escalated']} escalated to lecturer "
                          f"review, {s['attempts']} question(s) asked ({qdoc['meta']['tutor_label'].split(' (')[0]})", t)
            except Exception as exc:
                st.record("questions", "failed", failed(exc), t)
        return {"stages": st.items, "qdoc": qdoc, "trails": trails}

    # ---- report ----------------------------------------------------------------------------------------------------------------------------------
    def report(state: AssessState) -> dict:
        """The one place every path ends. Stages that did not run are filled in with the reason, every failure becomes an incomplete reason."""
        st = stages_of(state)
        for name in A.STAGES:  # in order, so the reasons are the same as when the stages ran one after the other
            if name not in st.items:
                why = st.blocked_by(name)
                st.skip(name, f"needs {why}" if why else "not reached")
        result, scan_report, idoc, tdoc, risk_doc, qdoc = (state.get(k) for k in ("result", "scan_report", "idoc", "tdoc", "risk_doc", "qdoc"))
        skipped, reused, trails = list(state.get("skipped", ctx.skip)), state.get("reused", False), dict(state.get("trails") or {})
        findings = A._collect(result, idoc, tdoc, risk_doc, qdoc, scan_report)
        pii.save_mapping(out / "pii_mapping.local.json")  # local only; written when the report had to replace personal data
        guidance_used = state.get("guidance_used") or {}
        stages = [st.items[n] for n in A.STAGES]
        reasons = [f"stage {s['stage']} {s['status']}: {s['detail']}" for s in stages if s["status"] not in A.OK]
        if gov.escalated:
            reasons.append(f"governance escalated for human review ({gov.escalation_reason}); read audit.jsonl")
        if gov.allowed:
            reasons.append(f"governance warn-only: {gov.allowed} call(s) were sent although a secret or personal-data check failed")
        if result is not None:
            reasons += [f"dependency coverage gap: {g}" for g in result.coverage_gaps]
        if skipped:
            reasons.append(f"tools skipped: {', '.join(skipped)}")
        if scan_report is not None:
            reasons += [f"coverage {c.value}: {v.level} - {v.note}" for c, v in scan_report.coverage.items() if v.level in ("NONE", "REDUCED")]
        scan_info = {"languages": result.languages if result else [],
                     "complete": bool(result and result.complete and not skipped and not result.coverage_gaps),
                     "skipped_tools": skipped, "warnings": result.warnings if result else [], "reused": reused,
                     "coverage_gaps": list(result.coverage_gaps) if result else [],
                     "tool_runs": [{"tool": r.tool, "status": r.status.value, "reason": r.reason, "tool_version": r.tool_version,
                                    "duration_s": r.duration_s, "findings_count": r.findings_count} for r in (result.runs if result else [])],
                     "coverage": {c.value: {"level": v.level, "note": v.note, "tools": v.tools}
                                  for c, v in (scan_report.coverage.items() if scan_report else [])}}
        doc = {
            "report_version": A.REPORT_VERSION,
            "meta": {"source": ctx.label, "commit_sha": ctx.ref if ctx.is_url else None, "threshold": ctx.threshold,
                     "llm_model": idoc["meta"]["model"] if idoc else None, "temperature": idoc["meta"].get("temperature") if idoc else None,
                     "interpreter_prompt": interp.PROMPT_VERSION,
                     "trace_prompt": tr.TRACE_PROMPT_VERSION, "risk_version": rk.RISK_VERSION,
                     "requirements_file": Path(ctx.requirements_file).name if ctx.requirements_file else None,
                     "tasks_file": Path(ctx.sprint_tasks_file).name if ctx.sprint_tasks_file else None},
            "run": {"complete": not reasons, "incomplete_reasons": reasons, "stages": stages, "llm_refused": bool(state.get("llm_refused"))},
            "scan": scan_info,
            "interpretation": idoc["summary"] if idoc else None,
            "llm_usage": A._usage(idoc, ctx.link_usage),
            "decision_trail": trails,
            "findings": findings,
            "dismissed": [x for x in (risk_doc["excluded"] if risk_doc else [])],
            "guidance": list(guidance_used.values()),
            "questions": {"meta": qdoc["meta"], "summary": qdoc["summary"]} if qdoc else None,
            "limitations": A._limitations(scan_info, idoc, qdoc, reused, bool(ctx.requirements_file or ctx.sprint_tasks_file)),
        }
        doc["meta"]["governance"] = "warn-only" if gov.warn_only else "enforce"

        def texts() -> tuple[str, str]:
            trails["Governance"] = gov.trail.entries
            doc["governance"] = gov.summary()
            return json.dumps(doc, indent=2, ensure_ascii=False), A.render(doc, state.get("scan_md", ""), idoc, tdoc, risk_doc, qdoc, findings)

        js_text, md_text = texts()
        leaks = gov.count_leaks_json(doc) + gov.count_leaks(md_text)  # the JSON is checked string by string: an escape such as \n is not text
        if leaks:  # a known secret or personal value reached the report: it is removed below, and the run says so
            gov.scrubbed = leaks
            reasons.append(f"governance removed {leaks} secret or personal value(s) that had reached the report")
            doc["run"].update(complete=False, incomplete_reasons=reasons)
            js_text, md_text = texts()
        (out / "report.json").write_text(gov.scrub_json(js_text, "report.json"), encoding="utf-8")
        (out / "report.md").write_text(gov.scrub(md_text, "report.md"), encoding="utf-8")
        manifest.write(out, manifest.build(report=doc, is_url=ctx.is_url, label=ctx.label, repo_url=str(ctx.repo_url) if ctx.is_url else None,
                                           commit_sha=scan_report.commit_sha if scan_report else None, seconds=time.monotonic() - ctx.t0))
        gov.end(complete=doc["run"]["complete"], reasons=len(reasons))
        return {"stages": st.items, "report": doc}

    builder = StateGraph(AssessState)
    for name, fn in (("fetch", fetch), ("scan", scan), ("governance", governance), ("interpret", interpret), ("trace", trace), ("risk", risk),
                     ("guidance", guidance), ("questions", questions), ("report", report)):
        builder.add_node(name, fn)
    builder.add_edge(START, "fetch")
    builder.add_conditional_edges("fetch", after_fetch, {"scan": "scan", "report": "report"})
    builder.add_conditional_edges("scan", after_scan, {"governance": "governance", "report": "report"})
    for a, b in (("governance", "interpret"), ("interpret", "trace"), ("trace", "risk"), ("risk", "guidance"), ("guidance", "questions"),
                 ("questions", "report")):
        builder.add_edge(a, b)
    builder.add_edge("report", END)
    return builder.compile()


def diagram_graph():
    """A compiled graph with no run behind it, for the diagram export only (the nodes are never run)."""
    return build_assess_graph(RunContext(
        repo_url="", requirements_file=None, sprint_tasks_file=None, reuse_scan=None, out=Path("."), allow_external_llm=False, client=None,
        tutor=None, threshold=0.7, ref=None, tools=None, max_findings=None, delay=0.0, retries=0, fetch_options=None, agent_config=None,
        orchestrator_policy=None, question_config=None, question_policy=None, say=lambda text: None, label="", is_url=False, gov=None, pii=None,
        stack=contextlib.AsyncExitStack()))
