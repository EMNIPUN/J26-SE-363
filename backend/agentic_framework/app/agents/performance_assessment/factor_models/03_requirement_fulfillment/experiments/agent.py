"""Experiment 2: a LangGraph agent that assesses one task by reading only what each criterion needs.

    map_commits -> decide <-> act -> record -> (next criterion) -> check -> END

- ``map_commits``: one model call that picks, from the student's own commit list, the commits that belong to the task (no mapping is given).
- ``decide`` / ``act``: for the current criterion the model chooses one JSON action: ``search`` the student's changed lines, ``read`` a
  hunk, or give the ``verdict`` with the evidence it cites. ``act`` runs the tool. At most ``MAX_STEPS`` actions per criterion; the last
  step must be a verdict.
- ``record``: stores the verdict and moves to the next criterion.
- ``check`` (plain code): every cited line must be a line a tool actually returned; a ``met`` or ``partly`` without valid evidence becomes
  ``cannot_tell``. The task value is then computed by the shared rule (``rf_bench.schema``); the model does no arithmetic.

All tools are the student-only tools of ``rf_bench.scope``: the model cannot name another student, and no tool returns a teammate's code.
"""

import json
import re
from typing import TypedDict

from langgraph.graph import END, StateGraph

from rf_bench import rubric
from rf_bench.llm import parse_json
from rf_bench.schema import est_tokens

MAX_STEPS = 4
MAX_TOKENS = 1200
OBS_CHARS = 3200          # one observation shown to the model, at most
KEEP_OBS = 3              # observations kept in the prompt for the current criterion
COMMITS_CHARS = 9000      # the commit list shown in the mapping call, at most

TOOLS = """You work by calling one of these functions each turn (call exactly one):
- search_my_changes(query): case-insensitive regular expression over the lines this student added; returns commit id, file, line index and the line.
- read_my_changes(sha, path, start): up to 80 changed lines of that file in that commit from the line index `start`.
- give_verdict(verdict, evidence, reason): your final answer for the current criterion. `evidence` lists {sha, path, lines: "first-last"} of lines a function returned to you.
Only this student's changed lines are available; you cannot see anyone else's code. A "met" or "partly" verdict without evidence you were shown is discarded.
You may use at most {steps} function calls for a criterion; the last one must be give_verdict. If you searched sensibly and found no implementation, the verdict is "not_met"."""

TOOL_DEFS = [
    {"type": "function", "function": {"name": "search_my_changes", "description": "Search the student's added lines with a case-insensitive regular expression.",
                                      "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "read_my_changes", "description": "Read up to 80 changed lines of one file in one of the student's commits.",
                                      "parameters": {"type": "object", "properties": {"sha": {"type": "string"}, "path": {"type": "string"}, "start": {"type": "integer"}}, "required": ["sha", "path"]}}},
    {"type": "function", "function": {"name": "give_verdict", "description": "Give the final verdict for the current criterion.",
                                      "parameters": {"type": "object", "properties": {
                                          "verdict": {"type": "string", "enum": ["met", "partly", "not_met", "cannot_tell"]},
                                          "evidence": {"type": "array", "items": {"type": "object", "properties": {"sha": {"type": "string"}, "path": {"type": "string"}, "lines": {"type": "string"}}, "required": ["sha", "path", "lines"]}},
                                          "reason": {"type": "string"}}, "required": ["verdict", "evidence", "reason"]}}},
]
ACTION_OF = {"search_my_changes": "search", "read_my_changes": "read", "give_verdict": "verdict"}

MAP_PROMPT = """{task}

Your commits in this sprint (id, date, message | files with counted changed lines):
{commits}

Commits whose message names this task: {hints}

Which of these commits belong to this task? Messages are often vague; use the files and the message. Reply with one JSON object: {{"commits": ["<id>", ...], "note": "<short>"}}. Use [] if none."""

DECIDE = """{task}

Commits that belong to this task (your selection): {mapped}
Files of those commits (counted changed lines): {files}

Criteria already decided: {done}

Current criterion: C{ci}. {criterion}
Actions used for it: {step} of {steps}.
{obs}
Choose your next action for C{ci}."""


class S(TypedDict, total=False):
    task: dict
    mapped: list
    files_text: str
    ci: int
    step: int
    obs: list
    action: dict
    verdicts: list
    notes: list
    error: str
    error_kind: str


def _llm_json(cfg, messages, tag, usage_key="usage"):
    llm, usage, run = cfg["llm"], cfg["usage"], cfg["run"]
    reply = usage.add(llm.chat(messages, max_tokens=MAX_TOKENS, temperature=0.0, tag=tag, seed=run))
    return reply, parse_json(reply.text) if reply.ok else None


def map_commits(state, config):
    cfg = config["configurable"]
    scope, task = cfg["scope"], state["task"]
    commits = scope.list_commits()
    cut = commits[:COMMITS_CHARS] + ("\n[list cut here]" if len(commits) > COMMITS_CHARS else "")
    hints = scope.task_commit_hints(task["id"])
    hint_shas = re.findall(r"^([0-9a-f]{10}) ", hints, re.M)
    messages = [{"role": "system", "content": rubric.RUBRIC}, {"role": "user", "content": MAP_PROMPT.format(task=rubric.task_block(task), commits=cut, hints=hints.replace(chr(10), "; "))}]
    reply, data = _llm_json(cfg, messages, f"agent:map:{task['id']}")
    own = scope.own_shas()
    picked = [s for s in (data or {}).get("commits", []) if isinstance(s, str) and s in own] if isinstance(data, dict) else []
    if not reply.ok:
        return {"error": reply.error, "error_kind": reply.error_kind, "mapped": hint_shas}
    mapped = sorted(set(picked) | set(hint_shas))
    files = []
    for s in mapped[:12]:
        c = cfg["bench"].commits[s]
        files.append(f"{s}: " + ", ".join(f"{f['path']}(+{f['added']}/-{f['deleted']})" for f in c["files"][:6]))
    return {"mapped": mapped, "files_text": "\n".join(files)[:2400] or "(none)", "ci": 0, "step": 0, "obs": [], "verdicts": [], "notes": [f"mapped {len(mapped)} commits"]}


def decide(state, config):
    cfg = config["configurable"]
    task, ci, step = state["task"], state["ci"], state["step"]
    done = "; ".join(f"C{i + 1} {v['verdict']}" for i, v in enumerate(state["verdicts"])) or "none"
    obs = "\n".join(f"Observation {i + 1}:\n{o}" for i, o in enumerate(state["obs"][-KEEP_OBS:])) or "No observations yet."
    last = step >= MAX_STEPS - 1
    user = DECIDE.format(task=rubric.task_block(task), mapped=", ".join(state["mapped"]) or "(none found)", files=state["files_text"], done=done, ci=ci + 1,
                         criterion=task["criteria"][ci], step=step, steps=MAX_STEPS, obs=obs)
    if last:
        user += "\nThis is your last action for this criterion: it must be a verdict."
    messages = [{"role": "system", "content": rubric.RUBRIC + "\n" + TOOLS.replace("{steps}", str(MAX_STEPS))}, {"role": "user", "content": user}]
    tools = [t for t in TOOL_DEFS if t["function"]["name"] == "give_verdict"] if last else TOOL_DEFS
    reply = cfg["usage"].add(cfg["llm"].chat(messages, max_tokens=MAX_TOKENS, temperature=0.0, tag=f"agent:decide:{task['id']}:C{ci + 1}:{step}", seed=cfg["run"], tools=tools))
    if not reply.ok and reply.error_kind == "bad_request" and ("tool_use_failed" in reply.error or "json_validate_failed" in reply.error):
        reply.error, reply.error_kind, reply.text, reply.tool_calls = "", "", "", []  # a malformed call: a wasted step, not a failure of the task
    if not reply.ok:
        return {"error": reply.error, "error_kind": reply.error_kind}
    if reply.tool_calls and reply.tool_calls[0]["name"] in ACTION_OF:
        action = {"action": ACTION_OF[reply.tool_calls[0]["name"]], **(reply.tool_calls[0]["arguments"] if isinstance(reply.tool_calls[0]["arguments"], dict) else {})}
    else:  # a model that answers in text (and the scripted model of the tests)
        data = parse_json(reply.text)
        action = data if isinstance(data, dict) and data.get("action") in ("search", "read", "verdict") else {"action": "invalid", "raw": (reply.text or "")[:120]}
    if last and action.get("action") != "verdict":
        action = {"action": "verdict", "verdict": "cannot_tell", "evidence": [], "reason": "out of steps"}
    return {"action": action}


def act(state, config):
    scope = config["configurable"]["scope"]
    a = state["action"]
    if a["action"] == "search":
        text = scope.search_changes(str(a.get("query", ""))[:200])
    elif a["action"] == "read":
        try:
            text = scope.read_hunk(str(a.get("sha", "")), str(a.get("path", "")), int(a.get("start", 0) or 0), 80)
        except (TypeError, ValueError):
            text = "invalid read request"
    else:
        text = "invalid reply: use one of search, read, verdict"
    return {"obs": state["obs"] + [text[:OBS_CHARS]], "step": state["step"] + 1}


def record(state, config):
    a = state["action"]
    v = rubric.normalise(a.get("verdict", ""))
    v = v if v in ("met", "partly", "not_met", "cannot_tell") else "cannot_tell"
    ev = a.get("evidence") if isinstance(a.get("evidence"), list) else []
    verdicts = state["verdicts"] + [{"verdict": v, "evidence": ev[:6], "reason": str(a.get("reason", ""))[:200], "steps": state["step"] + 1}]
    return {"verdicts": verdicts, "ci": state["ci"] + 1, "step": 0, "obs": []}


def _valid(scope, ev):
    """An evidence item is valid if at least one cited line is a changed line that a tool returned to the model."""
    try:
        sha, path = str(ev["sha"]), str(ev["path"])
        lo, hi = (str(ev["lines"]).replace(" ", "").split("-") + [None])[:2]
        lo = int(lo)
        hi = int(hi) if hi not in (None, "") else lo
    except Exception:
        return False
    return any((sha, path, i) in scope.seen for i in range(lo, min(hi, lo + 400) + 1))


def check(state, config):
    scope = config["configurable"]["scope"]
    out, ok = [], []
    for v in state["verdicts"]:
        valid = [e for e in v["evidence"] if isinstance(e, dict) and _valid(scope, e)]
        final = v["verdict"]
        if final in ("met", "partly") and not valid:
            final = "cannot_tell"
        ok.append(1.0 if (not v["evidence"] or len(valid) == len(v["evidence"])) else len(valid) / len(v["evidence"]))
        out.append({**v, "final": final, "valid_evidence": len(valid)})
    return {"verdicts": out, "notes": state.get("notes", []) + [f"cites_ok {sum(ok) / len(ok):.2f}" if ok else "no verdicts"]}


def route_after_decide(state, config):
    if state.get("error"):
        return "check"
    return "record" if state["action"]["action"] == "verdict" else "act"


def route_after_record(state, config):
    return "decide" if state["ci"] < len(state["task"]["criteria"]) else "check"


def route_after_map(state, config):
    return "check" if state.get("error") else "decide"


def build_graph():
    g = StateGraph(S)
    for name, fn in (("map_commits", map_commits), ("decide", decide), ("act", act), ("record", record), ("check", check)):
        g.add_node(name, fn)
    g.set_entry_point("map_commits")
    g.add_conditional_edges("map_commits", route_after_map, {"check": "check", "decide": "decide"})
    g.add_conditional_edges("decide", route_after_decide, {"check": "check", "record": "record", "act": "act"})
    g.add_edge("act", "decide")
    g.add_conditional_edges("record", route_after_record, {"decide": "decide", "check": "check"})
    g.add_edge("check", END)
    return g.compile()


GRAPH = build_graph()


class Agent:
    name = "agent"

    def config(self):
        return {"rubric_hash": rubric.RUBRIC_HASH, "prompt_hash": rubric.fingerprint(TOOLS, MAP_PROMPT, DECIDE, json.dumps(TOOL_DEFS)), "max_steps_per_criterion": MAX_STEPS, "max_tokens": MAX_TOKENS,
                "observation_chars": OBS_CHARS, "mapping": "found by the agent", "examples": 0, "graph": "map_commits -> decide <-> act -> record -> check"}

    def assess(self, bench, task_id, scope, llm, usage, run=0):
        task = bench.task_public(task_id)
        cfg = {"configurable": {"scope": scope, "llm": llm, "usage": usage, "run": run, "bench": bench}, "recursion_limit": 200}
        state = GRAPH.invoke({"task": task, "mapped": [], "verdicts": [], "notes": []}, cfg)
        return self.result(bench, task_id, task, scope, state)

    def result(self, bench, task_id, task, scope, state):
        """The result row of a finished graph state (shared by the experiments that extend the agent)."""
        truth_map = {c["sha"] for c in bench.task_commits(task_id)}
        mapped = set(state.get("mapped", []))
        out = {"mapping": sorted(mapped), "mapping_truth": sorted(truth_map),
               "mapping_precision": len(mapped & truth_map) / len(mapped) if mapped else None,
               "mapping_recall": len(mapped & truth_map) / len(truth_map) if truth_map else None,
               "coverage": round(scope.coverage(mapped or None), 4) if mapped else 0.0, "tool_calls": len(scope.calls), "notes": state.get("notes", [])}
        if state.get("error"):
            return {**out, "error": state["error"], "error_kind": state.get("error_kind", "")}
        vs = state["verdicts"]
        if len(vs) != len(task["criteria"]):
            return {**out, "error": "incomplete", "error_kind": "bad_output"}
        out["verdicts"] = [v["final"] for v in vs]
        out["raw_verdicts"] = [v["verdict"] for v in vs]
        out["reasons"] = [v["reason"] for v in vs]
        out["evidence"] = [v["evidence"] for v in vs]
        out["steps"] = [v["steps"] for v in vs]
        cited = [v for v in vs if v["verdict"] in ("met", "partly")]
        out["cites_ok"] = round(sum(1 for v in cited if v["valid_evidence"]) / len(cited), 4) if cited else None
        return out

    @staticmethod
    def dry_responder(messages, tag):
        """A scripted agent for tests: maps nothing, searches one word of the criterion, then answers from what it saw."""
        user = messages[-1]["content"]
        if ":map:" in tag:
            return '{"commits": [], "note": "scripted"}'
        m = re.search(r"Current criterion: C\d+\. (.*)", user)
        words = [w for w in re.findall(r"[A-Za-z]{5,}", m.group(1) if m else "")]
        seen = re.findall(r"^([0-9a-f]{10}) (\S+):(\d+): ", user, re.M)
        if "Observation 1" not in user:
            return json.dumps({"action": "search", "query": words[0] if words else "x"})
        if seen:
            sha, path, line = seen[0]
            return json.dumps({"action": "verdict", "verdict": "met", "evidence": [{"sha": sha, "path": path, "lines": f"{line}-{line}"}], "reason": "scripted"})
        return json.dumps({"action": "verdict", "verdict": "not_met", "evidence": [], "reason": "scripted"})
