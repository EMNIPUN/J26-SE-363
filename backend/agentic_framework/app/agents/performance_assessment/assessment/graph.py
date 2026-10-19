"""The assessment agent's graphs.

Team graph (one per run; checkpointed, so a run that waits for the lecturer's identity mapping continues after a restart):

    load_run_context -> prepare_workspace -> collect_scrum -> collect_github -> build_team_evidence -> evidence_quality_gate -> dispatch_students -> team_cross_check -> team_report -> publish
                                                                    ^------------- (after the lecturer maps authors) ----+

Student graph (one per student, run inside ``dispatch_students`` with bounded concurrency):

    student_evidence_check -> [factor_effort | factor_consistency | factor_collaboration | factor_task_complexity | rf_subagent] -> join_factors -> factor_audit -> ownership_quiz
                              -> behavioral_pattern -> fusion -> explain -> export

Every node runs inside ``Events.node(path)`` so the live pipeline view shows it. Only the identity gate can interrupt: the Code Ownership quiz and lecturer reviews never hold a thread.
A score only ever comes from a factor package; the agent's own steps (audit, explanation) read results and cannot write them.
"""
import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from shared.performance.topology import PASSIVE, RF_NODES, STUDENT_NODES, TEAM_NODES, topology  # noqa: F401

from app.agents.performance_assessment.assessment import audit, factors, justify, quiz_flow
from app.agents.performance_assessment.assessment.events import Events
from app.agents.performance_assessment.assessment.fusion import fuse
from app.agents.performance_assessment.assessment.report import build_report
from app.agents.performance_assessment.evidence_builder import Roster, build_team_evidence
from app.agents.performance_assessment.workspace import WorkspaceError

UNMAPPED_LIMIT = 0.10  # the run asks the lecturer when authors it cannot map wrote this share of the sprint's added lines
NODE_FOR_FACTOR = {"effort": "factor_effort", "consistency": "factor_consistency", "collaboration": "factor_collaboration", "task_complexity": "factor_task_complexity",
                   "requirement_fulfillment": "rf_subagent"}

def _merge(a, b):
    return {**(a or {}), **(b or {})}


class TeamState(TypedDict, total=False):
    run_id: str
    team_ref: str
    sprint_id: str
    mode: str
    repo_url: str
    board_ref: str
    sprint: dict
    students: list
    rebuild: bool
    rebuilt: bool
    gate: dict
    flags: list
    outcomes: dict
    report: str


class StudentState(TypedDict, total=False):
    results: Annotated[dict, _merge]
    actions: list
    reasoning: dict
    behavioral: dict
    fused: dict
    justification: dict
    status: str
    outcome: dict


def _safe(payload):
    if not isinstance(payload, dict):
        return {}
    return {k: v for k, v in payload.items() if isinstance(v, (int, float, bool)) or (isinstance(v, str) and len(v) < 200)}


# ======================================================================================================================================
# student graph
# ======================================================================================================================================

class StudentPipeline:
    def __init__(self, sv, ev: Events, run: dict, sid: str):
        self.sv, self.ev, self.run, self.sid = sv, ev, run, sid
        self.d = sv.data(run["id"])
        self.mode, self.team, self.sprint_id = run["mode"], run["team_ref"], run["sprint_id"]
        self.evidence = self.d.evidence[sid]
        self.provisional = self.mode != "final"
        self.context = {"llm": sv.llm, "on_event": self._rf_event}

    def path(self, node):
        return f"student:{self.sid}/{node}"

    def _rf_event(self, type, message, payload=None):  # called from the factor's thread
        self.ev.emit("log", f"{type}: {message}", node_path=self.path("rf_subagent"), payload=_safe(payload))

    def _save(self, name, r):
        self.sv.store.save_factor_result(self.run["id"], self.sid, name, score=r["score"], status=r["status"], interval=r["interval"], provisional=r["provisional"], features=r["features"],
                                         warnings=r["warnings"], versions=r["versions"])

    async def _run_factor(self, name):
        if name == "requirement_fulfillment":
            # the sub-agent calls a language model with blocking requests: keep it off the event loop so other students go on
            return await asyncio.to_thread(lambda: asyncio.run(factors.run_factor(name, self.evidence, patches_ref=str(self.d.patches_path), context=self.context)))
        return await factors.run_factor(name, self.evidence, context=self.context)

    def _wrap(self, node, fn):
        async def run(state):
            async with self.ev.node(self.path(node)) as n:
                return await fn(state, n)
        return run

    def _factor_node(self, name):
        async def fn(state, n):
            r = await self._run_factor(name)
            self._save(name, r)
            n.tool(name, f"{r['status']}" + (f" {r['score']:.3f}" if r["score"] is not None else ""))
            for w in r["warnings"][:5]:
                n.log(w, level="warn")
            n.result(status=r["status"], score=r["score"])
            return {"results": {name: r}}
        return fn

    async def check(self, state, n):
        e = self.evidence
        n.log(f"{len(e['commits'])} commits in the sprint, {len(e['tasks'])} tasks, {len(e.get('pull_requests', []))} pull requests, {len(e.get('reviews', []))} reviews")
        n.result(commits=len(e["commits"]), tasks=len(e["tasks"]))
        return {}

    async def join(self, state, n):
        r = state["results"]
        n.log(", ".join(f"{k}: {v['status']}" for k, v in sorted(r.items())))
        return {}

    async def audit_step(self, state, n):
        """Check the results; a factor that failed is run once more (the only automatic remedy), everything else waits for the final audit once the mark exists."""
        results = dict(state["results"])
        found = audit.findings(results, self.evidence)
        n.result(findings=len([f for f in found if f["severity"] != "info"]))
        for f in found:
            if f["severity"] != "info":
                n.log(f["message"], level="warn" if f["severity"] == "warn" else "error", finding=f["id"])
        for a in audit.decide(found, None):
            if a["action"] == "retry":
                n.log(f"re-running {a['factor']} once: {a['reason']}")
                r = await self._run_factor(a["factor"])
                self._save(a["factor"], r)
                results[a["factor"]] = r
        return {"results": results}

    async def quiz_step(self, state, n):
        if self.mode != "final":
            r = quiz_flow.pending("the code question is asked at the end of the sprint")
        else:
            quiz = await quiz_flow.issue(self.sv.store, self.sv.ws, self.run["repo_url"], self.d.rev, self.team, self.sprint_id, self.sid, self.evidence, self.run["id"], self.sv.token, self.sv.now())
            r = await quiz_flow.factor_for(self.sv.store, quiz)
            n.log(("quiz issued" if quiz and quiz["status"] == "open" else f"quiz {quiz['status']}" if quiz else "no suitable code for a quiz") + f"; Code Ownership {r['status']}")
        self._save("code_ownership", r)
        n.result(status=r["status"])
        return {"results": {**state["results"], "code_ownership": r}}

    async def behavioral_step(self, state, n):
        b = factors.run_behavioral(state["results"], provisional=self.provisional)
        n.log(f"pattern {b['persona']}" + ("" if b.get("applied") else " (shown as a tendency; no adjustment applied)"))
        n.result(persona=b["persona"])
        return {"behavioral": b}

    async def fusion_step(self, state, n):
        fused = fuse(state["results"], state["behavioral"])
        if fused["mark"] is None:
            n.log("no factor could be scored", level="warn")
        else:
            n.log(f"mark {fused['mark']:.1f} (plausible {fused['mark_interval'][0]:.0f} to {fused['mark_interval'][1]:.0f}); pending: {', '.join(fused['pending']) or 'none'}")
        n.result(mark=fused["mark"])
        return {"fused": fused}

    async def explain_step(self, state, n):
        results, fused = state["results"], state["fused"]
        previous = self.d.previous_marks.get(self.sid)
        found = audit.findings(results, self.evidence, previous, fused["mark"])
        summary = {k: {"score": r["score"], "status": r["status"]} for k, r in results.items()}
        reasoning = await asyncio.to_thread(audit.llm_decide, self.sv.llm, found, self.sv.cards, summary)
        actions = audit.decide(found, reasoning)
        for a in actions:
            n.log(f"{a['id']}: {a['action']} ({a['reason']})", level="warn" if a["action"] == "escalate" else "info")
            if a["action"] == "escalate" and not self._review_exists(a["id"]):
                self.sv.store.create_review(self.run["id"], "audit", f"{a['message']} | {a['reason']}", student_id=self.sid,
                                            evidence={"finding": a["id"], "factor": a["factor"], "mark": fused["mark"], "scores": summary})
        status = "pending_review" if any(a["action"] == "escalate" for a in actions) else ("final" if self.mode == "final" and not fused["pending"] else "provisional")
        just = justify.explain(self.sid, results, fused, self.evidence, self.sv.cards, actions, status)
        just["audit"] = {"actions": [{k: a[k] for k in ("id", "factor", "severity", "action", "reason")} for a in actions], "summary": (reasoning or {}).get("summary"), "model": (reasoning or {}).get("model")}
        if self.sv.llm is not None:
            friendly = await asyncio.to_thread(justify.polish, self.sv.llm, just)
            if friendly:
                just["friendly_summary"] = friendly
        n.result(status=status, actions=len(actions))
        return {"actions": actions, "reasoning": reasoning or {}, "justification": just, "status": status}

    def _review_exists(self, finding_id):
        return any((r.get("evidence") or {}).get("finding") == finding_id and r.get("student_id") == self.sid for r in self.sv.store.list_reviews(None, self.run["id"]))

    async def export_step(self, state, n):
        fused, results = state["fused"], state["results"]
        by_factor = {}
        for a in state["actions"]:
            by_factor.setdefault(a["factor"], []).append({"finding": a["id"], "action": a["action"], "reason": a["reason"]})
        for name, r in results.items():
            self.sv.store.save_factor_result(self.run["id"], self.sid, name, score=r["score"], status=r["status"], interval=r["interval"], provisional=r["provisional"], features=r["features"],
                                             warnings=r["warnings"], versions=r["versions"], audit={"decisions": by_factor.get(name, [])})
        compact = {k: {"score": r["score"], "status": r["status"], "interval": r["interval"], "provisional": r["provisional"]} for k, r in results.items()}
        compact["behavioral_pattern"] = {"persona": state["behavioral"].get("persona"), "applied": state["behavioral"].get("applied"), "modifier": state["behavioral"].get("modifier")}
        self.sv.store.save_assessment_result(self.run["id"], self.team, self.sprint_id, self.sid, mark=fused["mark"], mark_interval=fused["mark_interval"], status=state["status"], factors=compact,
                                             justification=state["justification"], flags=[a for a in state["justification"]["flags"]])
        n.result(status=state["status"])
        return {"outcome": {"mark": fused["mark"], "interval": fused["mark_interval"], "status": state["status"], "pending": fused["pending"], "factors": compact,
                            "flags": len(state["justification"]["flags"])}}

    def build(self):
        g = StateGraph(StudentState)
        g.add_node("student_evidence_check", self._wrap("student_evidence_check", self.check))
        for f in PASSIVE:
            g.add_node(NODE_FOR_FACTOR[f], self._wrap(NODE_FOR_FACTOR[f], self._factor_node(f)))
        for name, fn in (("join_factors", self.join), ("factor_audit", self.audit_step), ("ownership_quiz", self.quiz_step), ("behavioral_pattern", self.behavioral_step), ("fusion", self.fusion_step),
                         ("explain", self.explain_step), ("export", self.export_step)):
            g.add_node(name, self._wrap(name, fn))
        g.add_edge(START, "student_evidence_check")
        par = [NODE_FOR_FACTOR[f] for f in PASSIVE]
        for p in par:
            g.add_edge("student_evidence_check", p)
        g.add_edge(par, "join_factors")
        for a, b in (("join_factors", "factor_audit"), ("factor_audit", "ownership_quiz"), ("ownership_quiz", "behavioral_pattern"), ("behavioral_pattern", "fusion"), ("fusion", "explain"), ("explain", "export"),
                     ("export", END)):
            g.add_edge(a, b)
        return g.compile()

    async def execute(self):
        out = await self.build().ainvoke({"results": {}})
        return out["outcome"]


# ======================================================================================================================================
# team graph
# ======================================================================================================================================

def _days(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).date() if "T" in iso else date.fromisoformat(iso)


class TeamGraph:
    def __init__(self, sv):
        self.sv = sv

    def _wrap(self, node, fn):
        async def run(state):
            ev = Events(self.sv.store, state["run_id"])
            async with ev.node(f"team/{node}") as n:
                return await fn(state, n, ev)
        return run

    # -- nodes ----------------------------------------------------------------------------------------------------------------------
    async def load_run_context(self, state, n, ev):
        sv = self.sv
        team = sv.store.get_tracked_team(state["team_ref"])
        if not team:
            raise ValueError(f"team {state['team_ref']!r} is not tracked")
        d = sv.data(state["run_id"])
        cfg = team.get("config") or {}
        d.roster = cfg.get("roster") or []
        d.previous_marks = {r["student_id"]: r["mark"] for r in sv.store.latest_results(state["team_ref"], state["sprint_id"]) if r.get("mark") is not None}
        n.log(f"team {state['team_ref']}: repository {team['repo_url']}, board {team.get('board_ref') or state['team_ref']}, {len(d.roster)} students in the roster, mode {state['mode']}")
        n.result(students=len(d.roster))
        return {"repo_url": team["repo_url"], "board_ref": team.get("board_ref") or state["team_ref"]}

    async def prepare_workspace(self, state, n, ev):
        sv = self.sv
        await asyncio.to_thread(sv.ws.ensure_mirror, state["repo_url"], token=sv.token)
        n.tool("git fetch", "read-only mirror up to date")
        return {}

    async def collect_scrum(self, state, n, ev):
        sv, d = self.sv, self.sv.data(state["run_id"])
        async with sv.scrum() as scrum:
            det = await scrum.get_sprint_details(state["sprint_id"])
            n.tool("get_sprint_details", state["sprint_id"])
            if det.get("error"):
                raise ValueError(det["error"])
            if not d.roster:
                d.roster = [{"student_id": r["student_id"], "emails": [], "logins": [], "names": []} for r in await scrum.get_team_roster(state["board_ref"])]
                n.log("the tracking record has no roster; using the board's student ids (authors cannot be mapped until the lecturer adds e-mails or logins)", level="warn")
            d.sprint = {"id": state["sprint_id"], "team_id": state["team_ref"], "start": det["start_date"], "end": det["end_date"], "days": int(det.get("length_days") or 14)}
            tasks, count = {}, 0
            for s in d.roster:
                rows = await scrum.get_student_tasks(state["sprint_id"], s["student_id"])
                for t in rows:
                    crit = await scrum.get_task_acceptance_criteria(t["task_id"])
                    t["acceptance_criteria"] = crit.get("acceptance_criteria", [])
                    t["description"] = t.get("description") or crit.get("description", "")
                count += len(rows)
                tasks[s["student_id"]] = rows
            n.tool("get_student_tasks", f"{count} tasks for {len(d.roster)} students")
        d.tasks_by_student = tasks
        d.as_of = None
        if state["mode"] == "snapshot":
            now = sv.now()
            end = _days(d.sprint["end"])
            d.as_of = now.isoformat() if now.date() < end else None
            if d.as_of is None:
                n.log("the sprint is over: this snapshot is computed on the full sprint", level="info")
        return {"sprint": d.sprint, "students": [s["student_id"] for s in d.roster]}

    async def collect_github(self, state, n, ev):
        sv, d = self.sv, self.sv.data(state["run_id"])
        d.prs = None
        if sv.github is None:
            n.log("GitHub is not connected: Collaboration will be 'not available'", level="warn")
            return {}
        try:
            d.prs = await sv.github.pulls_bundle(state["repo_url"], since=d.sprint["start"])
            n.tool("pulls_bundle", f"{len(d.prs)} pull requests with reviews and comments")
        except Exception as e:  # rate limit, no access: the rest of the run goes on without the review data
            n.log(f"GitHub data could not be read ({type(e).__name__}); Collaboration will be 'not available'", level="warn")
        return {}

    async def build_team_evidence(self, state, n, ev):
        sv, d = self.sv, self.sv.data(state["run_id"])
        sprint = dict(d.sprint)
        if d.as_of:
            sprint["end"] = min(_days(sprint["end"]), _days(d.as_of)).isoformat()
        roster = Roster(d.roster)
        built = await asyncio.to_thread(build_team_evidence, sv.ws, state["repo_url"], roster, sprint, d.tasks_by_student, d.prs, token=sv.token)
        d.evidence, d.quality, d.rev, d.patches = built.evidence, built.quality, built.rev, built.patches
        if d.as_of:
            for e in d.evidence.values():
                e["as_of"] = d.as_of
        d.save()
        q = d.quality
        n.log(f"{q['commits_in_sprint']} commits in the sprint, {len(q['unmapped_authors'])} unmapped authors, {q['bot_commits']} bot commits; unmapped share of added lines {q['unmapped_share_of_added_lines']:.0%}")
        for note in q["notes"][:10]:
            n.log(note, level="warn")
        n.result(commits=q["commits_in_sprint"], unmapped=len(q["unmapped_authors"]))
        return {"rebuild": False}

    async def evidence_quality_gate(self, state, n, ev):
        sv, d = self.sv, self.sv.data(state["run_id"])
        q = d.quality
        need = q["unmapped_share_of_added_lines"] >= UNMAPPED_LIMIT and not state.get("rebuilt")
        if not need:
            n.log("evidence is complete enough to assess" + (f"; {len(q['unmapped_authors'])} unmapped authors are small and are listed in the report" if q["unmapped_authors"] else ""))
            return {"gate": {"passed": True}, "rebuild": False}
        if not any(r["kind"] == "identity_mapping" for r in sv.store.list_reviews(None, state["run_id"])):
            sv.store.create_review(state["run_id"], "identity_mapping", f"{q['unmapped_share_of_added_lines']:.0%} of the sprint's added lines are by authors that match no student",
                                   evidence={"unmapped_authors": q["unmapped_authors"], "roster": [s["student_id"] for s in d.roster]})
        sv.store.update_run(state["run_id"], status="waiting_human")
        decision = interrupt({"type": "identity_mapping", "unmapped_authors": q["unmapped_authors"], "roster": [s["student_id"] for s in d.roster]})
        sv.store.update_run(state["run_id"], status="running")
        mapping = (decision or {}).get("mapping") or []
        if not mapping:
            n.log("the lecturer chose to continue without mapping; the unmapped work is listed in the report")
            return {"gate": {"passed": True, "unmapped_accepted": True}, "rebuild": False, "rebuilt": True}
        by_id = {s["student_id"]: s for s in d.roster}
        for m in mapping:
            s = by_id.get(m.get("student_id"))
            if s:
                for key, field in (("email", "emails"), ("login", "logins"), ("name", "names")):
                    if m.get(key):
                        s.setdefault(field, []).append(m[key])
        team = sv.store.get_tracked_team(state["team_ref"])
        sv.store.update_tracked_config(state["team_ref"], {**(team.get("config") or {}), "roster": d.roster})
        n.log(f"{len(mapping)} authors mapped by the lecturer; evidence is built again")
        return {"gate": {"passed": True, "mapped": len(mapping)}, "rebuild": True, "rebuilt": True}

    async def dispatch_students(self, state, n, ev):
        sv, d = self.sv, self.sv.data(state["run_id"])
        run = sv.store.get_run(state["run_id"])
        run = {**run, "repo_url": state["repo_url"]}
        sem = asyncio.Semaphore(sv.parallel_students)
        out = {}

        async def one(sid):
            async with sem:
                try:
                    out[sid] = await StudentPipeline(sv, ev, run, sid).execute()
                except Exception as e:  # one student's failure must not stop the team
                    ev.emit("node_error", f"{type(e).__name__}: {str(e)[:300]}", node_path=f"student:{sid}", level="error")
                    out[sid] = {"mark": None, "interval": None, "status": "failed", "error": f"{type(e).__name__}: {str(e)[:200]}", "pending": [], "factors": {}, "flags": 0}

        await asyncio.gather(*(one(s) for s in state["students"]))
        failed = [s for s, o in out.items() if o["status"] == "failed"]
        n.log(f"{len(out) - len(failed)} of {len(out)} students assessed" + (f"; failed: {', '.join(failed)}" if failed else ""), level="warn" if failed else "info")
        n.result(students=len(out), failed=len(failed))
        return {"outcomes": out}

    async def team_cross_check(self, state, n, ev):
        d = self.sv.data(state["run_id"])
        flags = []
        claimed = {}
        for sid, tasks in d.tasks_by_student.items():
            for t in tasks:
                claimed.setdefault(t["task_id"], []).append(sid)
        for tid, who in claimed.items():
            if len(who) > 1:
                flags.append({"code": "task_claimed_twice", "message": f"task {tid} is assigned to {', '.join(who)}", "students": who})
        for author, u in d.quality.get("unmapped_authors", {}).items():
            flags.append({"code": "unmapped_author", "message": f"{author}: {u['commits']} commits, {u['lines']} added lines not attributed to anyone", "students": []})
        silent = [s for s, e in d.evidence.items() if not e["commits"]]
        if silent and len(silent) < len(d.evidence):
            flags.append({"code": "no_commits", "message": f"no counted commits in the sprint: {', '.join(silent)}", "students": silent})
        for f in flags:
            n.log(f["message"], level="warn")
        n.result(flags=len(flags))
        return {"flags": flags}

    async def team_report(self, state, n, ev):
        run = self.sv.store.get_run(state["run_id"])
        text = build_report(run, state.get("sprint") or {}, state.get("outcomes") or {}, state.get("flags") or [], self.sv.data(state["run_id"]).quality)
        n.log(f"report written ({len(text.splitlines())} lines)")
        return {"report": text}

    async def publish(self, state, n, ev):
        sv, d = self.sv, self.sv.data(state["run_id"])
        out = state.get("outcomes") or {}
        end = _days(d.sprint["end"]) if d.sprint else None
        as_of = datetime.fromisoformat(d.as_of) if d.as_of else datetime.combine(end or sv.now().date(), datetime.max.time(), tzinfo=timezone.utc)
        start = _days(d.sprint["start"])
        days = max(1, int(d.sprint.get("days") or 14))
        elapsed = 1.0 if not d.as_of else min(1.0, max(0.0, ((as_of.date() - start).days + 1) / days))
        for sid, o in out.items():
            if o["status"] != "failed":
                sv.store.add_snapshot(state["team_ref"], state["sprint_id"], sid, as_of, elapsed, mark=o["mark"], mark_interval=o["interval"], factors=o["factors"])
        marks = {s: o["mark"] for s, o in out.items()}
        pending = sorted({s for s, o in out.items() if o.get("pending")})
        sv.store.update_run(state["run_id"], summary={"students": len(out), "marks": marks, "pending_code_ownership": pending, "flags": state.get("flags", []), "report_markdown": state.get("report", ""),
                                                      "sprint_elapsed": elapsed, "quality": {k: d.quality.get(k) for k in ("commits_in_sprint", "unmapped_share_of_added_lines", "bot_commits")}})
        n.log(f"{len(out)} results published, {len(pending)} waiting for a quiz answer")
        return {}

    def build(self, checkpointer=None):
        g = StateGraph(TeamState)
        for name, _label in TEAM_NODES:
            g.add_node(name, self._wrap(name, getattr(self, name)))
        g.add_edge(START, "load_run_context")
        for a, b in (("load_run_context", "prepare_workspace"), ("prepare_workspace", "collect_scrum"), ("collect_scrum", "collect_github"), ("collect_github", "build_team_evidence"),
                     ("build_team_evidence", "evidence_quality_gate")):
            g.add_edge(a, b)
        g.add_conditional_edges("evidence_quality_gate", lambda s: "build_team_evidence" if s.get("rebuild") else "dispatch_students", {"build_team_evidence": "build_team_evidence", "dispatch_students": "dispatch_students"})
        for a, b in (("dispatch_students", "team_cross_check"), ("team_cross_check", "team_report"), ("team_report", "publish"), ("publish", END)):
            g.add_edge(a, b)
        return g.compile(checkpointer=checkpointer)
