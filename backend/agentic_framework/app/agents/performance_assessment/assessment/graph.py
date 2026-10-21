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
import os
import threading
import time
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from shared.performance.topology import PASSIVE, RF_NODES, STUDENT_NODES, TEAM_NODES, topology  # noqa: F401

from app.agents.performance_assessment.assessment import anomaly, audit, daily, factors, investigate, justify, quiz_flow
from app.agents.performance_assessment.assessment.events import Events
from app.agents.performance_assessment.assessment.fusion import fuse
from app.agents.performance_assessment.assessment.report import build_report
from app.agents.performance_assessment.evidence_builder import Roster, build_team_evidence
from app.agents.performance_assessment.workspace import WorkspaceError

UNMAPPED_LIMIT = 0.10  # the run asks the lecturer when authors it cannot map wrote this share of the sprint's added lines
ANOMALY_NODE = {"effort": "anomaly_effort", "consistency": "anomaly_consistency", "collaboration": "anomaly_collaboration", "task_complexity": "anomaly_task_complexity", "requirement_fulfillment": "anomaly_rf"}
NODE_FOR_FACTOR = {"effort": "factor_effort", "consistency": "factor_consistency", "collaboration": "factor_collaboration", "task_complexity": "factor_task_complexity",
                   "requirement_fulfillment": "rf_subagent"}

def _merge(a, b):
    return {**(a or {}), **(b or {})}


class TeamState(TypedDict, total=False):
    run_id: str
    team_ref: str
    sprint_id: str
    mode: str
    options: dict
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
    anomalies: Annotated[dict, _merge]
    actions: list
    reasoning: dict
    behavioral: dict
    fused: dict
    justification: dict
    status: str
    outcome: dict


FACTOR_TIMEOUT = float(os.environ.get("ASSESSMENT_FACTOR_TIMEOUT", 180))     # seconds a factor may take
RF_TIMEOUT = float(os.environ.get("ASSESSMENT_RF_TIMEOUT", 900))              # Requirement Fulfillment calls a language model for every criterion
STUDENT_TIMEOUT = float(os.environ.get("ASSESSMENT_STUDENT_TIMEOUT", 1800))   # seconds one student's whole pipeline may take


def stopped(name, seconds):
    """What a factor that ran out of time looks like: a failure the audit and the lecturer can see, never a score."""
    return {"factor": name, "score": None, "status": "fallback", "interval": None, "warnings": [f"{name} did not finish within {seconds:.0f} s and was stopped"], "versions": {}, "features": {},
            "provisional": False, "removed": {}, "tasks": None, "model": None}


def fuse_weights():
    from app.agents.performance_assessment.com_agent.fusion_engine.weights_config import get_weights_as_dict

    return get_weights_as_dict()


def _safe(payload):
    if not isinstance(payload, dict):
        return {}
    out = {}
    for k, v in payload.items():
        if isinstance(v, (int, float, bool)):
            out[k] = v
        elif isinstance(v, str):
            out[k] = v[:50000]
        elif isinstance(v, (list, dict)):
            out[k] = v
    return out


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
        self.memory = []  # this student's earlier sprints (marks, scores, what was flagged), read when the pipeline starts, so every explanation and check knows how the student did before
        self.cancel = threading.Event()  # tells the Requirement Fulfillment thread to stop between tasks when it ran out of time
        self.context = {"llm": sv.llm, "on_event": self._rf_event, "cancel": self.cancel}

    def path(self, node):
        return f"student:{self.sid}/{node}"

    def _rf_event(self, type, message, payload=None):  # called from the factor's thread
        path = self.path("rf_subagent")
        payload = _safe(payload)
        if type in {"task_start", "task_done", "task_skipped", "task_error"}:
            task = payload.pop("task", None)
            if task:
                self.ev.task(path, type, task, **payload)
            else:
                self.ev.emit("task", message, node_path=path, payload={"event": type, **payload})
        elif type in {"rf_thinking", "thinking"}:
            self.ev.emit("thinking", message or "Agent Reasoning", node_path=path, payload=payload)
        elif type in {"rf_tool", "tool"}:
            tool_name = (payload or {}).get("tool", "tool")
            self.ev.emit("tool", message or f"Tool: {tool_name}", node_path=path, payload=payload)
        elif type in {"rf_decision", "decision"}:
            self.ev.emit("decision", message or "Decision Reached", node_path=path, payload=payload)
        elif type in {"rf_node_start", "node_start"}:
            sub_node = (payload or {}).get("node", "decide")
            self.ev.emit("log", f"Phase started: {sub_node}", node_path=path, payload={"subnode": sub_node, **payload})
        elif type in {"rf_node_end", "node_end"}:
            sub_node = (payload or {}).get("node", "decide")
            self.ev.emit("log", f"Phase completed: {sub_node}", node_path=path, payload={"subnode": sub_node, **payload})
        elif type in {"rf_log", "log"}:
            self.ev.emit("log", message, node_path=path, payload=payload)
        elif type == "llm_call":
            import re
            match = re.search(r":\s*(\d+)\+(\d+)\s+tokens(?:,\s*([\d.]+)s)?", message)
            self.ev.llm(path, message,
                purpose=payload.get("tag", "requirement_fulfillment"),
                model=getattr(self.sv.llm, "model", ""),
                prompt_tokens=int(match.group(1)) if match else 0,
                completion_tokens=int(match.group(2)) if match else 0,
                seconds=float(match.group(3)) if match and match.group(3) else 0,
                ok=True, refused=False)
        elif type == "llm_error":
            self.ev.llm(path, message, purpose=payload.get("tag", "requirement_fulfillment"), model=getattr(self.sv.llm, "model", ""), prompt_tokens=0, completion_tokens=0, seconds=0, ok=False, refused=True)
        else:
            self.ev.emit("log", f"{type}: {message}", node_path=path, payload=payload)

    async def _save(self, name, r):
        await self.sv.astore.save_factor_result(self.run["id"], self.sid, name, score=r["score"], status=r["status"], interval=r["interval"], provisional=r["provisional"], features=r["features"],
                                                warnings=r["warnings"], versions=r["versions"])

    async def _run_factor(self, name):
        limit = RF_TIMEOUT if name == "requirement_fulfillment" else FACTOR_TIMEOUT
        try:
            if name == "requirement_fulfillment":
                # the sub-agent calls a language model with blocking requests: keep it off the event loop so other students go on
                work = asyncio.to_thread(lambda: asyncio.run(factors.run_factor(name, self.evidence, patches_ref=str(self.d.patches_path), context=self.context)))
            else:
                work = factors.run_factor(name, self.evidence, context=self.context)
            return await asyncio.wait_for(work, limit)
        except asyncio.TimeoutError:
            self.cancel.set()
            return stopped(name, limit)

    def _wrap(self, node, fn):
        async def run(state):
            async with self.ev.node(self.path(node)) as n:
                return await fn(state, n)
        return run

    def _factor_node(self, name):
        async def fn(state, n):
            r = await self._run_factor(name)
            await self._save(name, r)
            n.tool(name, f"{r['status']}" + (f" {r['score']:.3f}" if r["score"] is not None else ""))
            for w in r["warnings"][:5]:
                n.log(w, level="warn")
            n.result(status=r["status"], score=r["score"])
            n.produce(f"factors.{name}.*", verified=True)
            return {"results": {name: r}}
        return fn

    async def load_memory(self):
        """What the agent remembers of this student from the sprints before this one: stored marks, factor scores and flags, oldest first."""
        team = await self.sv.astore.get_tracked_team(self.team)
        sprints = sorted(((team or {}).get("config") or {}).get("sprints") or [], key=lambda x: x.get("start", ""))
        start = (self.d.sprint or {}).get("start", "")
        rows = []
        for sp in sprints:
            if sp["id"] == self.sprint_id or sp.get("start", "") >= start:
                continue
            rows += [r for r in await self.sv.astore.latest_results(self.team, sp["id"]) if r["student_id"] == self.sid and r.get("mark") is not None]
        self.memory = anomaly.memory_of(rows)

    def _anomaly_node(self, name):
        async def fn(state, n):
            r = state["results"].get(name) or {}
            found = anomaly.rules(name, r, self.evidence, self.memory)
            found += await asyncio.to_thread(anomaly.review, self.sv.llm, name, r, self.evidence, self.sv.cards.get(name), self.memory, found)
            for a in found:
                n.log(a["message"], level="warn" if a["severity"] == "warn" else "info", finding=a["id"])
            n.tool("anomaly_check", f"{len(found)} finding{'s' if len(found) != 1 else ''}" + (f", {len(self.memory)} earlier sprint{'s' if len(self.memory) != 1 else ''} considered" if self.memory else ""))
            n.result(findings=len(found))
            return {"anomalies": {name: found}}
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
                await self._save(a["factor"], r)
                results[a["factor"]] = r
        return {"results": results}

    async def quiz_step(self, state, n):
        if self.mode != "final":
            r = quiz_flow.pending("the code question is asked at the end of the sprint")
        else:
            quiz = await quiz_flow.issue(self.sv.store, self.sv.ws, self.run["repo_url"], self.d.rev, self.team, self.sprint_id, self.sid, self.evidence, self.run["id"], await self.sv.token_for(self.d), self.sv.now(), llm=self.sv.llm)
            r = await quiz_flow.factor_for(self.sv.store, quiz)
            n.log(("quiz issued" if quiz else "no suitable code for a quiz") + f"; Code Ownership {r['status']}")
        await self._save("code_ownership", r)
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
        started = time.time()
        reasoning = await asyncio.to_thread(investigate.run, self.sv.llm, found, self.sv.cards, results, self.evidence, await self._history(previous))
        if reasoning is None:  # the investigation gave no usable answer: ask for the decisions directly
            reasoning = await asyncio.to_thread(audit.llm_decide, self.sv.llm, found, self.sv.cards, summary)
        for t in (reasoning or {}).get("trace", []):
            n.tool(t["tool"], t["result"][:140], args=_safe(t["args"]))
            # Keep the pre-v2 event path readable by existing consumers while the graph
            # topology exposes this work under the more precise "investigate" node.
            n.events.emit("tool", f"{t['tool']}: {t['result'][:140]}", node_path=f"student:{self.sid}/explain",
                          payload={"tool": t["tool"], "args": _safe(t["args"])})
        if (reasoning or {}).get("thinking") or (reasoning or {}).get("summary"):
            # the auditor's own reasoning and its conclusion on whether the results can be trusted
            said = "\n\n".join(x for x in (reasoning.get("thinking"), f"Conclusion: {reasoning['summary']}" if reasoning.get("summary") else "") if x)
            n.thinking("Checking my own results", thinking=said, duration=round(time.time() - started, 1))
        changed = {}
        overrides = (reasoning or {}).get("overrides") or {}
        if overrides:
            changed = investigate.apply_overrides(results, overrides)
            results = {**results, **changed}
            for f, why in overrides.items():
                n.log(f"{f} left out of the mark by the auditor: {why}", level="warn")
            state_behavioral = factors.run_behavioral(results, provisional=self.provisional)
            fused = fuse(results, state_behavioral)
            n.log(f"mark composed again without it: {fused['mark'] if fused['mark'] is None else round(fused['mark'], 1)}")
            found = audit.findings(results, self.evidence, previous, fused["mark"])
        else:
            state_behavioral = state["behavioral"]
        actions = audit.decide(found, reasoning)
        for a in actions:
            n.log(f"{a['id']}: {a['action']} ({a['reason']})", level="warn" if a["action"] == "escalate" else "info")
            if a["action"] == "escalate" and not await self._review_exists(a["id"]):
                await self.sv.astore.create_review(self.run["id"], "audit", f"{a['message']} | {a['reason']}", student_id=self.sid,
                                            evidence={"finding": a["id"], "factor": a["factor"], "mark": fused["mark"], "scores": summary})
        status = "pending_review" if any(a["action"] == "escalate" for a in actions) else ("final" if self.mode == "final" and not fused["pending"] else "provisional")
        just = justify.explain(self.sid, results, fused, self.evidence, self.sv.cards, actions, status, anomalies=state.get("anomalies"), memory=self.memory)
        just["audit"] = {"actions": [{k: a[k] for k in ("id", "factor", "severity", "action", "reason")} for a in actions], "summary": (reasoning or {}).get("summary"), "model": (reasoning or {}).get("model"),
                         "checked": [{"tool": t["tool"], "result": t["result"][:200]} for t in (reasoning or {}).get("trace", [])], "left_out": overrides}
        facts = just.pop("_narration_facts", {})
        narrated = await asyncio.to_thread(justify.narrate, self.sv.llm, facts, just.get("evidence"))
        slots = narrated["slots"]
        just["generated"] = narrated["generated"]
        just["friendly_summary"] = slots.get("hero_summary", just["summary"])
        just["brief"] = {"text": slots.get("brief", just["summary"])}
        just["headline"] = just["summary"].split(". ", 1)[0]
        just["key"] = [{"kind": s["kind"], "lead": s["kind"].replace("_", " ").title(), "text": slots[s["id"]]}
                       for s in facts.get("slots", []) if s["id"].startswith("key.") and s["id"] in slots]
        just["more"] = [{"kind": s["kind"], "lead": s["kind"].replace("_", " ").title(), "text": slots[s["id"]]}
                        for s in facts.get("slots", []) if s["id"].startswith("more.") and s["id"] in slots]
        for name, block in just["factors"].items():
            if name in justify.TITLES and f"factor.{name}" in slots:
                block["explain"] = {"in_short": slots[f"factor.{name}"], "based_on": block.get("reasons", [])}
        # the last thing the trace shows for this student: the explanation of the mark, as the lecturer will read it
        n.events.emit("summary", f"Summary for {self.sid}", node_path=n.path,
                      payload={"student": self.sid, "mark": fused["mark"], "status": status, "text": just["friendly_summary"], "brief": just["brief"]["text"]})
        n.result(status=status, actions=len(actions))
        return {"actions": actions, "reasoning": reasoning or {}, "justification": just, "status": status, "results": changed, "fused": fused, "behavioral": state_behavioral}

    async def _history(self, previous):
        """What compare_with_history shows the auditor: the student's earlier snapshots of this sprint and the previous result."""
        rows = await self.sv.astore.trajectory(self.team, self.sprint_id, self.sid)
        return {"previous_mark": previous, "snapshots": [{"day": str(r["as_of"])[:10], "mark": r["mark"], "sprint_elapsed": round(r["sprint_elapsed"], 2),
                                                          "scores": {k: v.get("score") for k, v in (r["factors"] or {}).items() if isinstance(v, dict) and "score" in v}} for r in rows[-8:]]}

    async def _review_exists(self, finding_id):
        return any((r.get("evidence") or {}).get("finding") == finding_id and r.get("student_id") == self.sid for r in await self.sv.astore.list_reviews(None, self.run["id"]))

    async def export_step(self, state, n):
        fused, results = state["fused"], state["results"]
        by_factor = {}
        for a in state["actions"]:
            by_factor.setdefault(a["factor"], []).append({"finding": a["id"], "action": a["action"], "reason": a["reason"]})
        store, rid, sid = self.sv.store, self.run["id"], self.sid

        def save_factors():
            for name, r in results.items():
                store.save_factor_result(rid, sid, name, score=r["score"], status=r["status"], interval=r["interval"], provisional=r["provisional"], features=r["features"],
                                         warnings=r["warnings"], versions=r["versions"], audit={"decisions": by_factor.get(name, [])})

        await asyncio.to_thread(save_factors)
        compact = {k: {"score": r["score"], "status": r["status"], "interval": r["interval"], "provisional": r["provisional"]} for k, r in results.items()}
        compact["behavioral_pattern"] = {"persona": state["behavioral"].get("persona"), "applied": state["behavioral"].get("applied"), "modifier": state["behavioral"].get("modifier")}
        await self.sv.astore.save_assessment_result(self.run["id"], self.team, self.sprint_id, self.sid, mark=fused["mark"], mark_interval=fused["mark_interval"], status=state["status"], factors=compact,
                                             justification=state["justification"], flags=[a for a in state["justification"]["flags"]])
        n.result(status=state["status"])
        return {"outcome": {"mark": fused["mark"], "interval": fused["mark_interval"], "status": state["status"], "pending": fused["pending"], "factors": compact,
                            "flags": len(state["justification"]["flags"]), "notes": justify.early_warning_notes(results, fused)}}

    async def curate_evidence_step(self, state, n):
        n.result(groups=len(justify.curate_evidence(state["results"], self.evidence)))
        return {}

    async def narrate_step(self, state, n):
        generated = state.get("justification", {}).get("generated", {})
        n.result(generated=bool(generated))
        for field in ("friendly_summary", "brief.text", "why.key", "why.more", "factors.*.explain", "pattern.note"):
            n.produce(field, verified=bool(generated.get("verified")), fallback=field in generated.get("fallback_fields", []))
        return {}

    async def verify_text_step(self, state, n):
        generated = state.get("justification", {}).get("generated", {})
        n.result(verified=generated.get("verified", False), fallback_fields=generated.get("fallback_fields", []))
        for field in generated.get("fallback_fields", []):
            n.produce(field, fallback=True)
        return {}

    def build(self):
        g = StateGraph(StudentState)
        g.add_node("student_evidence_check", self._wrap("student_evidence_check", self.check))
        for f in PASSIVE:
            g.add_node(NODE_FOR_FACTOR[f], self._wrap(NODE_FOR_FACTOR[f], self._factor_node(f)))
        async def no_op(state, n):
            return {}

        for name, fn in (("join_factors", self.join), ("factor_audit", self.audit_step), ("quiz_generate", no_op), ("ownership_quiz", self.quiz_step), ("behavioral_pattern", self.behavioral_step), ("fusion", self.fusion_step),
                         ("investigate", self.explain_step), ("justify", no_op), ("curate_evidence", self.curate_evidence_step),
                         ("narrate", self.narrate_step), ("verify_text", self.verify_text_step), ("design_reviews", no_op), ("export", self.export_step)):
            g.add_node(name, self._wrap(name, fn))
        g.add_edge(START, "student_evidence_check")
        par = [NODE_FOR_FACTOR[f] for f in PASSIVE]
        for p in par:
            g.add_edge("student_evidence_check", p)
        for f in PASSIVE:  # an anomaly check after each factor, then the join
            g.add_node(ANOMALY_NODE[f], self._wrap(ANOMALY_NODE[f], self._anomaly_node(f)))
            g.add_edge(NODE_FOR_FACTOR[f], ANOMALY_NODE[f])
        g.add_edge([ANOMALY_NODE[f] for f in PASSIVE], "join_factors")
        for a, b in (("join_factors", "factor_audit"), ("factor_audit", "quiz_generate"), ("quiz_generate", "ownership_quiz"), ("ownership_quiz", "behavioral_pattern"), ("behavioral_pattern", "fusion"), ("fusion", "investigate"),
                     ("investigate", "justify"), ("justify", "curate_evidence"), ("curate_evidence", "narrate"), ("narrate", "verify_text"), ("verify_text", "design_reviews"), ("design_reviews", "export"),
                     ("export", END)):
            g.add_edge(a, b)
        return g.compile()

    async def execute(self):
        try:
            await self.load_memory()
        except Exception:  # no memory is not a reason to stop: the sprint is assessed without it
            self.memory = []
        out = await self.build().ainvoke({"results": {}, "anomalies": {}})
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
        team = await sv.astore.get_tracked_team(state["team_ref"])
        if not team:
            raise ValueError(f"team {state['team_ref']!r} is not tracked")
        d = sv.data(state["run_id"])
        cfg = team.get("config") or {}
        d.roster = cfg.get("roster") or []
        d.installation_id = cfg.get("installation_id")  # the GitHub App installation of a platform team; its token is minted when needed and never stored
        d.simulate_now = cfg.get("simulate_now")  # test aid: take a snapshot as if it were this moment (set directly in the database)
        d.scrum_data_dir = cfg.get("scrum_data_dir")  # set directly in the database for a board that lives outside the course dataset; the API never accepts it
        d.previous_marks = {r["student_id"]: r["mark"] for r in await sv.astore.latest_results(state["team_ref"], state["sprint_id"]) if r.get("mark") is not None}
        n.log(f"team {state['team_ref']}: repository {team['repo_url']}, board {team.get('board_ref') or state['team_ref']}, {len(d.roster)} students in the roster, mode {state['mode']}")
        n.result(students=len(d.roster))
        return {"repo_url": team["repo_url"], "board_ref": team.get("board_ref") or state["team_ref"]}

    async def prepare_workspace(self, state, n, ev):
        sv = self.sv
        await asyncio.to_thread(sv.ws.ensure_mirror, state["repo_url"], token=await sv.token_for(sv.data(state["run_id"])))
        n.tool("git fetch", "read-only mirror up to date")
        return {}

    async def collect_scrum(self, state, n, ev):
        sv, d = self.sv, self.sv.data(state["run_id"])
        try:
            scrum_context = sv.scrum(
                d.scrum_data_dir,
                repo_url=state["repo_url"],
                team_ref=state["team_ref"],
            )
        except TypeError:
            # Preserve test and legacy providers that only accept the data directory.
            scrum_context = sv.scrum(d.scrum_data_dir) if d.scrum_data_dir else sv.scrum()
        async with scrum_context as scrum:
            det = await scrum.get_sprint_details(state["sprint_id"])
            n.tool("get_sprint_details", state["sprint_id"])
            if det.get("error"):
                raise ValueError(det["error"])
            if not d.roster:
                d.roster = [
                    {
                        "student_id": r["student_id"],
                        "emails": [r["email"]] if r.get("email") else [],
                        "logins": [],
                        "names": [r["name"]] if r.get("name") else [],
                    }
                    for r in await scrum.get_team_roster(state["board_ref"])
                ]
                n.log("the tracking record has no roster; using the board's student ids and fixture e-mail mappings", level="warn")
            d.sprint = {"id": state["sprint_id"], "team_id": state["team_ref"], "start": det["start_date"], "end": det["end_date"], "days": int(det.get("length_days") or 14)}
            board_roster = await scrum.get_team_roster(state["board_ref"])
            board_id_for = {}
            for br in (board_roster or []):
                b_email = (br.get("email") or "").strip().lower()
                b_id = br.get("student_id")
                b_name = (br.get("name") or "").strip().lower()
                for s in d.roster:
                    s_emails = [e.strip().lower() for e in s.get("emails", [])]
                    s_names = [nm.strip().lower() for nm in s.get("names", [])]
                    if s["student_id"] == b_id or (b_email and b_email in s_emails) or (b_name and b_name in s_names):
                        board_id_for[s["student_id"]] = b_id
                        break

            tasks, count = {}, 0
            for s in d.roster:
                query_id = board_id_for.get(s["student_id"], s["student_id"])
                rows = await scrum.get_student_tasks(state["sprint_id"], query_id)
                if not rows and query_id != s["student_id"]:
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
            now = datetime.fromisoformat(d.simulate_now) if d.simulate_now else sv.now()
            end = _days(d.sprint["end"])
            d.as_of = now.isoformat() if now.date() < end else None
            if d.as_of is None:
                n.log("the sprint is over: this snapshot is computed on the full sprint", level="info")
        all_students = [s["student_id"] for s in d.roster]
        selected = (state.get("options") or {}).get("students")
        if selected:
            active_students = [s for s in all_students if s in selected]
            if not active_students:
                active_students = all_students
        else:
            active_students = all_students
        return {"sprint": d.sprint, "students": active_students}

    async def collect_github(self, state, n, ev):
        sv, d = self.sv, self.sv.data(state["run_id"])
        d.prs = None
        token = await sv.token_for(d)
        github = sv.github
        if github is None:
            from app.agents.performance_assessment.com_agent.ingestion.github_rest import GitHubREST

            github = GitHubREST(token)  # without a token a public repository can still be read, within GitHub's 60 requests an hour
        try:
            d.prs = await github.pulls_bundle(state["repo_url"], since=d.sprint["start"])
            try:  # a fork's pull requests live in the repository it was forked from: read those too, or the team's reviews are never seen
                origin = await github.upstream_of(state["repo_url"]) if hasattr(github, "upstream_of") else None
                if origin:
                    taken = {x["number"] for x in d.prs}
                    extra = await github.pulls_bundle(origin, since=d.sprint["start"])
                    d.prs += [{**x, "number": x["number"] + (100000 if x["number"] in taken else 0)} for x in extra]
                    n.tool("pulls_bundle", f"{len(extra)} pull requests also read from the original repository {origin.rsplit('github.com/', 1)[-1]}")
            except Exception as e:
                n.log(f"the original repository of this fork could not be read: {type(e).__name__}: {str(e)[:120]}", level="warn")
            if d.prs:
                n.tool("pulls_bundle", f"{len(d.prs)} pull requests with reviews and comments")
            else:
                # nothing is made up: with no pull requests there are no reviews to read, and Collaboration says so
                n.tool("pulls_bundle", "0 pull requests in the repository")
                n.log("the repository has no pull requests: the team may commit straight to the main branch, so Collaboration has nothing to read", level="warn")
        except Exception as e:  # rate limit, no access
            d.prs = []
            n.tool("pulls_bundle", f"GitHub could not be read ({type(e).__name__})")
            n.log(f"pull requests could not be read from GitHub: {type(e).__name__}: {str(e)[:160]}; Collaboration is left out", level="warn")
        return {}

    async def build_team_evidence(self, state, n, ev):
        sv, d = self.sv, self.sv.data(state["run_id"])
        sprint = dict(d.sprint)
        if d.as_of:
            sprint["end"] = min(_days(sprint["end"]), _days(d.as_of)).isoformat()
        roster = Roster(d.roster)
        token = await sv.token_for(d)
        built = await asyncio.to_thread(lambda: build_team_evidence(sv.ws, state["repo_url"], roster, sprint, d.tasks_by_student, d.prs, token=token, progress=lambda m: n.log(m)))
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
        if need:
            # authors the lecturer already chose to leave unmapped (in an earlier sprint of this team) are not asked about again
            team = await sv.astore.get_tracked_team(state["team_ref"])
            accepted = set(((team or {}).get("config") or {}).get("accepted_unmapped") or [])
            if set(q["unmapped_authors"]) <= accepted:
                n.log("the lecturer already chose to leave these authors unmapped in an earlier sprint; continuing")
                need = False
        if not need:
            n.log("evidence is complete enough to assess" + (f"; {len(q['unmapped_authors'])} unmapped authors are small and are listed in the report" if q["unmapped_authors"] else ""))
            return {"gate": {"passed": True}, "rebuild": False}
        if not any(r["kind"] == "identity_mapping" for r in await sv.astore.list_reviews(None, state["run_id"])):
            await sv.astore.create_review(state["run_id"], "identity_mapping", f"{q['unmapped_share_of_added_lines']:.0%} of the sprint's added lines are by authors that match no student",
                                   evidence={"unmapped_authors": q["unmapped_authors"], "roster": [s["student_id"] for s in d.roster]})
        await sv.astore.update_run(state["run_id"], status="waiting_human")
        decision = interrupt({"type": "identity_mapping", "unmapped_authors": q["unmapped_authors"], "roster": [s["student_id"] for s in d.roster]})
        await sv.astore.update_run(state["run_id"], status="running")
        mapping = []
        for m in (decision or {}).get("mapping") or []:
            author = str(m.get("author") or "")  # an answer given as "Name <email>" and a student
            if author and not (m.get("email") or m.get("name")):
                m = {**m, "email": author.rsplit("<", 1)[-1].rstrip("> ").strip() if "<" in author else None, "name": author.split("<")[0].strip() or None}
            mapping.append(m)
        if not mapping:
            n.log("the lecturer chose to continue without mapping; the unmapped work is listed in the report")
            team = await sv.astore.get_tracked_team(state["team_ref"])
            cfg = dict((team or {}).get("config") or {})
            cfg["accepted_unmapped"] = sorted(set(cfg.get("accepted_unmapped") or []) | set(q["unmapped_authors"]))
            await sv.astore.update_tracked_config(state["team_ref"], cfg)
            return {"gate": {"passed": True, "unmapped_accepted": True}, "rebuild": False, "rebuilt": True}
        by_id = {s["student_id"]: s for s in d.roster}
        for m in mapping:
            s = by_id.get(m.get("student_id"))
            if s:
                for key, field in (("email", "emails"), ("login", "logins"), ("name", "names")):
                    if m.get(key):
                        s.setdefault(field, []).append(m[key])
        team = await sv.astore.get_tracked_team(state["team_ref"])
        # authors the lecturer chose not to map are "not in this team": later sprints do not ask about them again
        mapped_emails = {(m.get("email") or "").lower() for m in mapping if m.get("email")}
        mapped_names = {(m.get("name") or "").lower() for m in mapping if m.get("name")}
        left = [a for a in q["unmapped_authors"] if not ((a.rsplit("<", 1)[-1].rstrip("> ").lower() in mapped_emails) or (a.split("<")[0].strip().lower() in mapped_names))]
        cfg = {**(team.get("config") or {}), "roster": d.roster}
        cfg["accepted_unmapped"] = sorted(set(cfg.get("accepted_unmapped") or []) | set(left))
        await sv.astore.update_tracked_config(state["team_ref"], cfg)
        n.log(f"{len(mapping)} authors mapped by the lecturer; evidence is built again")
        return {"gate": {"passed": True, "mapped": len(mapping)}, "rebuild": True, "rebuilt": True}

    async def dispatch_students(self, state, n, ev):
        sv, d = self.sv, self.sv.data(state["run_id"])
        run = await sv.astore.get_run(state["run_id"])
        run = {**run, "repo_url": state["repo_url"]}
        sem = asyncio.Semaphore(sv.parallel_students)
        out = {}

        async def one(sid):
            async with sem:
                try:
                    out[sid] = await asyncio.wait_for(StudentPipeline(sv, ev, run, sid).execute(), STUDENT_TIMEOUT)
                except asyncio.TimeoutError:
                    ev.emit("node_error", f"the pipeline of {sid} did not finish within {STUDENT_TIMEOUT:.0f} s and was stopped", node_path=f"student:{sid}", level="error")
                    out[sid] = {"mark": None, "interval": None, "status": "failed", "error": f"timed out after {STUDENT_TIMEOUT:.0f} s", "pending": [], "factors": {}, "flags": 0}
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

    async def team_narrative(self, state, n, ev):
        """Deterministic run headline and readable quality notes; no score calculations."""
        outcomes = state.get("outcomes") or {}
        marks = [o["mark"] for o in outcomes.values() if o.get("mark") is not None]
        quality = self.sv.data(state["run_id"]).quality
        headline = f"{len(marks)} student{'s' if len(marks) != 1 else ''} assessed"
        notes = list(quality.get("notes") or [])
        if quality.get("unmapped_authors"):
            notes.append(f"{len(quality['unmapped_authors'])} author(s) could not be matched to a student.")
        n.result(headline=headline, quality_notes=len(notes))
        return {"team_narrative": {"headline": headline, "quality_notes": notes}}

    async def team_report(self, state, n, ev):
        run = await self.sv.astore.get_run(state["run_id"])
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
                await sv.astore.add_snapshot(state["team_ref"], state["sprint_id"], sid, as_of, elapsed, mark=o["mark"], mark_interval=o["interval"], factors=o["factors"])
        # the mark as it stood at the end of every earlier day of the sprint, for the day-by-day chart (a snapshot taken mid-sprint stops the day before it)
        for sid, o in out.items():
            if o["status"] == "failed" or sid not in d.evidence:
                continue
            try:
                points = await daily.trajectory(d.evidence[sid], start, end, days, as_of.date() if d.as_of else None)
                for p in points:
                    await sv.astore.add_snapshot(state["team_ref"], state["sprint_id"], sid, p["as_of"], p["elapsed"], mark=p["mark"], mark_interval=p["interval"], factors=p["factors"])
                n.tool("daily_marks", f"{len(points)} days for {sid}")
            except Exception as e:  # the chart is an extra; the results are already published
                n.log(f"day-by-day marks of {sid} could not be worked out: {type(e).__name__}: {str(e)[:160]}", level="warn")
        marks = {s: o["mark"] for s, o in out.items()}
        pending = sorted({s for s, o in out.items() if o.get("pending")})
        early_warnings = {s: o.get("notes", {}) for s, o in out.items() if o.get("notes")}
        method = {"weights": fuse_weights(), "factors": {n: {k: c.get(k) for k in ("title", "measures", "validation", "limits", "warnings")} for n, c in sv.cards.items()}}
        narrative = state.get("team_narrative") or {}
        await sv.astore.update_run(state["run_id"], summary={"method": method, "students": len(out), "marks": marks, "pending_code_ownership": pending, "flags": state.get("flags", []), "report_markdown": state.get("report", ""),
                                                      "headline": narrative.get("headline", f"{len(out)} students assessed"), "quality_notes": narrative.get("quality_notes", []),
                                                      "early_warning_notes": early_warnings,
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
        for a, b in (("dispatch_students", "team_cross_check"), ("team_cross_check", "team_narrative"), ("team_narrative", "team_report"), ("team_report", "publish"), ("publish", END)):
            g.add_edge(a, b)
        return g.compile(checkpointer=checkpointer)
