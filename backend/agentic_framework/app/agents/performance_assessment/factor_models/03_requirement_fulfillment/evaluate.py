"""Production entry point of the Requirement Fulfillment factor (looked up by com_agent/factor_bridge.py).

    evaluate(payload, context) -> {factor, score, interval, features, removed, versions, warnings, provisional, tasks: [...]}

``payload``: ``{"evidence": <evidence/1 of one student>, "patches": {sha: {path: patch}} | None, "patches_ref": "<path of a json file with the patches>" | None}``. The language-model sub-agent
(LangGraph, with a critic of another model family; see EXPERIMENTS.md) judges each task's acceptance criteria from the student's own changed lines; the arithmetic is plain code
(rf_bench.schema: criterion verdict values met 1, partly 0.5, not met / cannot tell 0; task value = mean; sprint score = mean over the student's tasks). The model never does arithmetic.

``context["llm"]`` is the language-model client (a GroqPool built from GROQ_API_KEYS if absent; ScriptedLLM in tests). Without a client or keys the score is "not available", never a guess.
``context["on_event"]``, if given, is called with ``(type, message, payload)`` for each task, so the live pipeline can show progress.

The sprint score has a rough band only: on the 10-task development smoke the critic version's task-level MAE was 0.34 (EXPERIMENTS.md); no held-out run was finished.
"""
import asyncio
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))


class NotEnoughEvidence(ValueError):
    """The score is not available (the bridge records a fallback and fusion redistributes the weight)."""


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _default_llm():
    from rf_bench.llm import GroqPool
    try:
        return GroqPool()
    except RuntimeError as e:
        raise NotEnoughEvidence(f"no language-model client: {e}") from e


# ---- verdicts that need not be judged again ---------------------------------------------------------------------------------------------------
# A task's verdicts depend on exactly four things: the task (its text and criteria), the student's changed lines the model is shown, the prompts and rubric, and the model.
# When none of them changed since an earlier run (a nightly snapshot of a quiet team, a re-run, a quiz answer that re-composes a student), the earlier verdicts are used and the
# model is not called. The key is a hash of those four things, so any change to any of them judges the task again. Only clean results are kept (no error, no "cannot tell"),
# so a verdict the model could not reach is never frozen. Switched on by RF_CACHE_DIR (the worker sets it inside its workspace); RF_CACHE=0 turns it off.

def _cache_dir():
    if os.environ.get("RF_CACHE", "1").strip().lower() in ("0", "false", "no", "off"):
        return None
    d = os.environ.get("RF_CACHE_DIR")
    return Path(d) if d else None


def _task_key(bench, tid, agent, llm):
    commits = [{"sha": c["sha"], "message": c.get("message", ""), "files": [{"path": f["path"], "added": f["added"], "deleted": f["deleted"], "hunk": bench.hunk(c["sha"], f["path"])} for f in c["files"]]}
               for c in bench.student_commits(bench.sprint, bench.student)]
    blob = json.dumps({"v": 1, "task": bench.task_public(tid), "commits": commits, "agent": agent.config(), "model": getattr(llm, "model", "")}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _cache_get(key):
    d = _cache_dir()
    if d is None:
        return None
    try:
        return json.loads((d / f"{key}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _cache_put(key, res):
    d = _cache_dir()
    if d is None or res.get("error") or not res.get("verdicts") or "cannot_tell" in res["verdicts"]:
        return
    try:
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / f".{key}.{os.getpid()}.tmp"
        tmp.write_text(json.dumps(res), encoding="utf-8")
        os.replace(tmp, d / f"{key}.json")
    except (OSError, TypeError, ValueError):
        pass  # a cache that cannot be written is only a missed speed-up


class _Traced:
    """The language-model client, with one event per call (what was asked, how long it took, whether it was refused). It changes nothing about the calls."""

    def __init__(self, inner, emit):
        self._inner, self._emit = inner, emit
        self.model = getattr(inner, "model", "")

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def chat(self, messages, **kw):
        reply = self._inner.chat(messages, **kw)
        tag = kw.get("tag", "")
        if reply.ok:
            reasoning = getattr(reply, "reasoning", "") or ""
            latency = getattr(reply, "latency", 0.0)
            if reasoning:
                parts = tag.split(":")
                ci = parts[3] if len(parts) > 3 else ""
                summary = f"Reasoning about {ci}" if ci else f"Reasoning for {tag}"
                self._emit("rf_thinking", summary, {
                    "thinking": reasoning,
                    "tag": tag,
                    "duration": latency,
                    "summary": summary
                })
            for tc in getattr(reply, "tool_calls", []):
                self._emit("rf_tool", f"Tool call: {tc.get('name')}", {
                    "tool": tc.get("name"),
                    "args": tc.get("arguments", {}),
                    "tag": tag
                })
            prompt_tokens = getattr(reply, "prompt_tokens", 0)
            completion_tokens = getattr(reply, "completion_tokens", 0)
            attempts = getattr(reply, "attempts", 1)
            self._emit("llm_call", f"{tag}: {prompt_tokens}+{completion_tokens} tokens, {latency:.1f}s" + (f", {attempts} attempts" if attempts > 1 else ""), {"tag": tag})
        else:
            self._emit("llm_error", f"{tag}: {reply.error_kind or 'error'}: {str(reply.error)[:120]} ({reply.attempts} attempts)", {"tag": tag})
        return reply


def evaluate(payload, context=None):
    from rf_bench.runner import Usage
    from rf_bench.scope import Scope
    from rf_bench.schema import band, sprint_score, task_fulfilment
    from rf_live import EvidenceBench

    ctx = context or {}
    ev = payload.get("evidence", payload)
    if not isinstance(ev, dict) or ev.get("schema") != "evidence/1":
        raise ValueError("requirement_fulfillment: the payload holds no evidence/1")
    patches = payload.get("patches")
    if patches is None and payload.get("patches_ref"):
        patches = json.loads(Path(payload["patches_ref"]).read_text(encoding="utf-8"))
    bench = EvidenceBench(ev, patches)
    task_ids = bench.tasks_of(bench.sprint, bench.student)
    if not task_ids:
        raise NotEnoughEvidence("no tasks with acceptance criteria are assigned to this student in the sprint")
    provisional = bool(ev.get("as_of"))
    judged = [t for t in task_ids if bench.should_judge(t, provisional)]
    skipped = [t for t in task_ids if t not in judged]
    llm = ctx.get("llm")
    if judged and llm is None:
        llm = _default_llm()
    emit = ctx.get("on_event") or (lambda *a, **k: None)
    if llm is not None:
        llm = _Traced(llm, emit)
    agent_mod = "experiments.agent_critic" if ctx.get("rf_critic", True) else "experiments.agent"
    agent = importlib.import_module(agent_mod)
    agent = getattr(agent, "AgentCritic" if ctx.get("rf_critic", True) else "Agent")()
    values, rows, warnings = {}, [], []
    usage = Usage()
    no_view = []
    cached_tasks = 0
    for tid in judged:
        if ctx.get("cancel") is not None and ctx["cancel"].is_set():
            warnings.append("stopped before all tasks were judged: out of time")
            break
        if not bench.commits:  # none of this student's changed lines is visible: there is nothing to show the model, and a model call would only cost time
            no_view.append(tid)
            rows.append({"task": tid, "status": "no_visible_change", "fulfilment": None})
            warnings.append(f"task {tid}: none of this student's changed lines in the sprint can be shown, so it was not sent to the model")
            emit("task_skipped", f"task {tid}: no changed lines of this student to judge", {"task": tid})
            continue
        scope = Scope(bench, bench.sprint, bench.student)
        emit("task_start", f"judging task {tid}", {"task": tid})
        key = _task_key(bench, tid, agent, llm) if _cache_dir() is not None else None
        res = _cache_get(key) if key else None
        reused = res is not None
        if res is None:
            res = agent.assess(bench, tid, scope, llm, usage, on_event=emit)
            if key:
                _cache_put(key, res)
        if res.get("error"):
            warnings.append(f"task {tid}: not judged ({res['error']})")
            rows.append({"task": tid, "status": "error", "error": res["error"]})
            emit("task_error", f"task {tid}: {res['error']}", {"task": tid})
            continue
        v = task_fulfilment(res["verdicts"])
        values[tid] = v
        if "cannot_tell" in res["verdicts"]:
            warnings.append(f"task {tid}: some criteria could not be decided from the code shown")
        rows.append({"task": tid, "status": "judged", "fulfilment": round(v, 4), "band": band(v), "verdicts": res["verdicts"], "reasons": res.get("reasons"), "evidence": res.get("evidence"),
                     "coverage": res.get("coverage"), "critic": res.get("critic")})
        if reused:
            cached_tasks += 1
        emit("task_done", f"task {tid}: fulfilment {v:.2f}" + (" (reused from an earlier run: nothing changed, no model call)" if reused else ""), {"task": tid, "verdicts": res["verdicts"], "reused": reused})
    if not provisional:
        for tid in no_view:
            values[tid] = 0.0  # the sprint is over and the task is claimed, but none of the student's changes can be seen
    for tid in skipped:
        values[tid] = 0.0
        rows.append({"task": tid, "status": "not_started" if not provisional else "not_ready", "fulfilment": 0.0 if not provisional else None})
    if provisional:
        scored = {t: v for t, v in values.items() if t in judged and t not in no_view}
        if not scored:
            raise NotEnoughEvidence("no task is Done or In Review yet, so nothing can be judged")
        values = scored
        warnings.append("provisional: only tasks that are Done or In Review are judged")
    if no_view and len(no_view) == len(judged) and provisional:
        raise NotEnoughEvidence("no changed lines of this student can be shown for the tasks that are Done or In Review, so nothing can be judged yet")
    if not any(r["status"] == "judged" for r in rows) and judged and len(no_view) < len(judged):
        raise NotEnoughEvidence("the language model could not judge any task: " + "; ".join(warnings)[:300])
    score = sprint_score(list(values.values()))
    spread = 0.34
    features = {"RF_tasks_assigned": len(task_ids), "RF_tasks_judged": sum(1 for r in rows if r["status"] == "judged"), "RF_tasks_not_started": len(skipped), "RF_llm_score": round(score, 4),
                "RF_cannot_tell_tasks": sum(1 for r in rows if r.get("verdicts") and "cannot_tell" in r["verdicts"]), "RF_tasks_reused": cached_tasks}
    return {"factor": "requirement_fulfillment", "score": round(score, 4), "interval": [round(max(0.0, score - spread), 4), round(min(1.0, score + spread), 4)], "features": features, "removed": {},
            "versions": {"agent": agent_mod, "rubric": __import__("rf_bench.rubric", fromlist=["x"]).RUBRIC_HASH}, "warnings": warnings, "provisional": provisional, "tasks": rows, "usage": usage.as_dict(),
            "model": getattr(llm, "model", "") if llm else ""}


async def async_evaluate(payload, context=None):
    if isinstance(payload, dict) and (payload.get("evidence") or payload.get("schema") == "evidence/1"):
        return await asyncio.to_thread(evaluate, payload, context)
    ctx = context or {}
    mode = ctx.get("simulation_mode") or os.getenv("FACTOR_SIMULATION_MODE", "quick")
    duration = 0.01 if "pytest" in sys.modules else None
    sim = _load("rf_simulate", "simulate.py")
    return await sim.async_simulate(payload=payload, mode=mode, duration_seconds=duration)
