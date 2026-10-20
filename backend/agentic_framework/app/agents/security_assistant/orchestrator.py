"""Analysis Orchestrator Agent: a bounded loop that works towards a complete findings report.

    outcome = await orchestrate(repo, tools=default_tools(), config=LoopConfig(max_steps=20, max_retries=1))
    outcome.result      # a ScanResult, like run_all's
    outcome.trail       # the decisions, also written to audit.jsonl and rendered into the report

GOAL      a findings report with every category covered (FULL, or nothing to scan) and no open dependency coverage gap.
STATE     which tools ran, their latest status, retries used per tool, coverage per category, the open and recorded coverage gaps,
          the steps used.
ACTIONS   a fixed list, valid in code (agent_loop.select): run_tools, retry_tool, codeql_per_language, scan_declared, record_gap,
          skip_with_reason, stop. There is no other way to act: no shell, no command text, only these actions on the repository's own
          tools. Tools are the detection adapters of tools/ and nothing else.
LOOP      after every action the state is recomputed and the next action chosen from the options valid in that state, until the goal is
          met, nothing is left to try, or the step budget is spent. The default policy is a set of deterministic rules; a policy that
          picks an LLM can replace it and may only pick one of the options it is shown.

What each action does:
  run_tools            the first pass: every tool whose precondition holds (right language, a lockfile for npm-audit, a requirements file for
                       pip-audit). A tool whose precondition fails is not run and is recorded as not applicable with the reason.
  retry_tool           run a failed or timed-out tool again (at most `max_retries` times per tool; a missing binary is never retried).
  codeql_per_language  after CodeQL failed (and its retries are spent) in a repository with several languages: run CodeQL once per language, so
                       one language that fails does not cost the others. The result keeps the findings of the languages that worked and
                       is marked failed unless all of them worked.
  scan_declared        after the full OSV-Scanner run failed (retries spent): run it only on the folder of a requirements file, whose declared
                       versions it can read; a smaller run may succeed where the full one did not.
  record_gap           accept a dependency coverage gap as a known, reported hole. When no tool supports the gap (for example a package.json
                       dependency that is not in the lockfile), the reason says why: reading declared npm versions would need `npm install`.
  skip_with_reason     acknowledge a tool that cannot be run or retried (binary missing, retries spent) so the loop can end honestly.
  stop                 always valid; says whether the goal was met, nothing is left to try, or the budget is spent.
"""

import asyncio
import os
import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.agents.security_assistant.agent_loop import Action, DecisionTrail, LoopConfig, Policy, RulePolicy, select
from app.agents.security_assistant.graphs.orchestrator_graph import build_orchestrator_graph, recursion_limit
from app.agents.security_assistant.report import coverage
from app.agents.security_assistant.schemas import Finding, RunStatus, ScanResult, ToolRun
from app.agents.security_assistant.tools.base import BaseTool, ScanContext
from app.agents.security_assistant.tools.codeql import CODEQL_LANGUAGES
from app.agents.security_assistant.tools.coverage_gaps import DEPENDENCY_TOOLS, find_dependency_gaps
from app.agents.security_assistant.tools.languages import detect_languages, walk_repo
from app.agents.security_assistant.tools.runner import _default_parallel, _scan_root, default_tools

ACTIONS = ("run_tools", "retry_tool", "codeql_per_language", "scan_declared", "record_gap", "skip_with_reason", "stop")
ACCEPTABLE = ("FULL", "NOTHING TO SCAN")
RETRYABLE = (RunStatus.FAILED, RunStatus.TIMED_OUT)  # a missing binary or an inapplicable tool will not get better
NO_TOOL = {  # why no tool of the allowed list can check a declared dependency, by kind of gap
    "npm": "no tool reads package.json without a lockfile; npm would have to install packages, which is never done",
    "python-project": "no tool reads pyproject.toml dependencies without a lockfile or pinned requirements",
    "maven": "OSV-Scanner already resolves pom.xml online; a dependency without a resolvable version cannot be checked",
    "gradle": "build.gradle is never read and gradle is never run; only gradle.lockfile is read",
    "other": "no tool of the allowed list supports this kind of manifest",
}


def gap_kind(gap: str) -> str:
    if "package.json" in gap:
        return "npm"
    if "without an exact version" in gap:
        return "requirements"
    if "pyproject.toml" in gap:
        return "python-project"
    if "pom.xml" in gap:
        return "maven"
    if "build.gradle" in gap:
        return "gradle"
    return "other"


@dataclass
class OrchestrationResult:
    result: ScanResult
    trail: list[dict]
    steps: int
    stop_reason: str
    goal_met: bool
    recorded_gaps: list[str] = field(default_factory=list)
    acknowledged: dict[str, str] = field(default_factory=dict)


class Orchestrator:
    def __init__(self, repo: Path | None, tools: list[BaseTool], *, policy: Policy | None = None, config: LoopConfig | None = None,
                 audit=None, skipped=(), scan_dir: Path | None = None, existing: ScanResult | None = None):
        self.repo = Path(repo).resolve() if repo is not None else None
        self.tools = {t.name: t for t in tools}
        self.order = [t.name for t in tools]
        self.policy = policy or RulePolicy()
        self.rules = RulePolicy()
        self.cfg = config or LoopConfig.from_env("ORCHESTRATOR", max_steps=20, max_retries=1)
        self.cfg = LoopConfig(max_steps=max(2, self.cfg.max_steps), max_retries=self.cfg.max_retries)  # a first pass and a stop need two
        self.trail = DecisionTrail("orchestrator", audit)
        self.skipped = sorted(skipped)
        self.scan_dir = scan_dir
        self.step = 0
        self.passed = False
        self.runs: dict[str, ToolRun] = {}
        self.findings: dict[str, list[Finding]] = {}
        self.retries_used: Counter = Counter()
        self.codeql_parts: dict[str, tuple[list[Finding], ToolRun]] = {}
        self.declared_done: set[str] = set()
        self.acknowledged: dict[str, str] = {}
        self.recorded_gaps: list[str] = []
        self.languages: set[str] = set()
        self.ctx: ScanContext | None = None
        self.gaps: list[str] = []
        self.run_id = uuid.uuid4().hex[:12]
        if existing is not None:  # review mode: the tools already ran (a reused scan); only gaps and acknowledgements are decided
            self.runs = {r.tool: r for r in existing.runs}
            self.findings = {}
            for f in existing.findings:
                self.findings.setdefault(f.tool, []).append(f)
            self.languages, self.gaps, self.passed, self.run_id = set(existing.languages), list(existing.coverage_gaps), True, existing.run_id
            self._existing = existing
            for name, run in self.runs.items():
                if run.status in RETRYABLE:
                    self.retries_used[name] = self.cfg.max_retries  # nothing can run in review mode: retries are spent
        else:
            self._existing = None
            if self.repo is None or not self.repo.is_dir():
                raise ValueError(f"not a directory: {repo}")
            self.languages = detect_languages(self.repo)
            work = _scan_root(self.repo, scan_dir) / self.run_id
            work.mkdir(parents=True, exist_ok=True)
            self.ctx = ScanContext(repo=self.repo, work_dir=work, languages=self.languages, run_id=self.run_id)
            if any(n in DEPENDENCY_TOOLS for n in self.tools):
                self.gaps = find_dependency_gaps(self.repo)

    # ---- state ---------------------------------------------------------------------------------------------------------------------
    def _levels(self) -> dict[str, str]:
        return {c.value: v.level for c, v in coverage(list(self.runs.values()), self.skipped).items()}

    def _open_gaps(self) -> list[str]:
        return [g for g in self.gaps if g not in self.recorded_gaps]

    def _hole(self) -> str:
        weak = [f"{c} {lv}" for c, lv in self._levels().items() if lv not in ACCEPTABLE]
        return ", ".join(weak)

    def goal_met(self) -> bool:
        return self.passed and all(lv in ACCEPTABLE for lv in self._levels().values()) and not self.gaps

    def state_summary(self) -> dict:
        return {"pass_done": self.passed, "statuses": {n: r.status.value for n, r in self.runs.items()},
                "retries_used": dict(self.retries_used), "coverage": self._levels(), "open_gaps": len(self._open_gaps()),
                "recorded_gaps": len(self.recorded_gaps), "steps_used": self.step, "max_steps": self.cfg.max_steps}

    # ---- the valid actions of the current state ---------------------------------------------------------------------------------------
    def precondition(self, name: str) -> str | None:
        """Why a tool should not run on this repository (None = run it)."""
        tool = self.tools[name]
        if tool.languages is not None and not (tool.languages & self.languages):
            return f"no {'/'.join(sorted(tool.languages))} files in the repository"
        names = [n for _d, ns in walk_repo(self.repo) for n in ns]
        if name == "npm-audit" and "package.json" in names and not any(n in ("package-lock.json", "npm-shrinkwrap.json") for n in names):
            return "no package-lock.json: OSV-Scanner only (a lockfile would need npm install, which is never run)"
        if name == "pip-audit" and not any(re.fullmatch(r"requirements[\w.-]*\.txt", n, re.I) for n in names):
            return "no requirements file: OSV-Scanner only"
        return None

    def options(self) -> list[Action]:
        if self.step + 1 >= self.cfg.max_steps:  # the last allowed decision is the stop
            return [Action("stop", why=f"budget spent: {self.cfg.max_steps} steps")]
        opts: list[Action] = []
        if not self.passed:
            selected = [n for n in self.order if n not in self.skipped and self.precondition(n) is None]
            held = {n: self.precondition(n) for n in self.order if n not in self.skipped and self.precondition(n)}
            why = f"first pass: run {len(selected)} tool(s)" + ("; not run: " + "; ".join(f"{n} ({r})" for n, r in held.items()) if held else "")
            return [Action("run_tools", "all", why), self._stop()]
        for name in self.order:
            run = self.runs.get(name)
            if run and run.status in RETRYABLE and self.retries_used[name] < self.cfg.max_retries and name not in self.acknowledged:
                opts.append(Action("retry_tool", name, f"{name} {run.status.value}; retry {self.retries_used[name] + 1} of {self.cfg.max_retries}"))
        codeql = self.runs.get("codeql")
        if codeql and "codeql" in self.tools and codeql.status in RETRYABLE and self.retries_used["codeql"] >= self.cfg.max_retries \
                and "codeql" not in self.acknowledged:
            groups = [g for g, (detected, _s) in CODEQL_LANGUAGES.items() if detected & self.languages]
            if len(groups) > 1:
                for g in groups:
                    if g not in self.codeql_parts:
                        opts.append(Action("codeql_per_language", g, f"codeql {codeql.status.value} with {len(groups)} languages; try {g} on its own"))
                        break
        osv = self.runs.get("osv-scanner")
        for gap in self._open_gaps():
            if gap_kind(gap) == "requirements" and "osv-scanner" in self.tools and osv and osv.status in RETRYABLE \
                    and self.retries_used["osv-scanner"] >= self.cfg.max_retries:
                target = gap.split(" lists ")[0]
                folder = str(Path(target).parent).replace("\\", "/")
                if folder not in self.declared_done:
                    opts.append(Action("scan_declared", folder, f"osv-scanner {osv.status.value} on the whole repository; read the declared versions of {target} only"))
        for gap in self._open_gaps():
            if not any(a.name == "scan_declared" and a.target == str(Path(gap.split(" lists ")[0]).parent).replace("\\", "/") for a in opts):
                kind = gap_kind(gap)
                opts.append(Action("record_gap", gap[:120], f"{gap}. Declared versions cannot be scanned: {NO_TOOL.get(kind, NO_TOOL['other']) if kind != 'requirements' else 'OSV-Scanner already read the requirements as written'}"))
        for name in (self.order or list(self.runs)):
            run = self.runs.get(name)
            if run and name not in self.acknowledged and (run.status is RunStatus.UNAVAILABLE or (
                    run.status in RETRYABLE and self.retries_used[name] >= self.cfg.max_retries and not any(
                        a.name in ("codeql_per_language", "scan_declared") for a in opts))):
                opts.append(Action("skip_with_reason", name, f"{name} {run.status.value}" + (f" ({run.reason})" if run.reason else "") +
                                   "; nothing more can be tried for it, so it stays a reported hole"))
        opts.append(self._stop())
        return opts

    def _stop(self) -> Action:
        if self.goal_met():
            return Action("stop", why="goal met: every category is FULL or has nothing to scan, and there is no coverage gap")
        if self._hole() == "" and self.gaps:
            return Action("stop", why=f"coverage acceptable; {len(self.recorded_gaps)} dependency gap(s) recorded and left open: "
                                      f"no tool of the allowed list can check them ({', '.join(sorted({gap_kind(g) for g in self.gaps}))})")
        return Action("stop", why=f"nothing left to try; remaining holes: {self._hole() or 'none'}"
                                  + (f"; {len(self._open_gaps())} gap(s) open" if self._open_gaps() else ""))

    # ---- the actions ----------------------------------------------------------------------------------------------------------------------
    async def _run_one(self, name: str, ctx: ScanContext) -> tuple[list[Finding], ToolRun]:
        return await self.tools[name].run(ctx)

    async def execute(self, action: Action) -> str:
        if action.name == "run_tools":
            held = {n: self.precondition(n) for n in self.order if n not in self.skipped and self.precondition(n)}
            selected = [n for n in self.order if n not in self.skipped and n not in held]
            limit = asyncio.Semaphore(_default_parallel())

            async def one(n):
                async with limit:
                    return n, await self._run_one(n, self.ctx)

            for n, (fs, run) in await asyncio.gather(*(one(n) for n in selected)):
                self.runs[n], self.findings[n] = run, fs
            for n, why in held.items():
                self.runs[n] = ToolRun(tool=n, status=RunStatus.NOT_APPLICABLE, reason=why, started_at=datetime.now(timezone.utc))
                self.findings[n] = []
            self.passed = True
            return ", ".join(f"{n} {self.runs[n].status.value}" for n in selected + list(held))
        if action.name == "retry_tool":
            name = action.target
            before = self.runs[name].status.value
            self.retries_used[name] += 1
            self.findings[name], self.runs[name] = await self._run_one(name, self.ctx)
            return f"{name}: {before} -> {self.runs[name].status.value}"
        if action.name == "codeql_per_language":
            group = action.target
            detected = CODEQL_LANGUAGES[group][0] & self.languages
            sub = ScanContext(repo=self.repo, work_dir=self.ctx.work_dir, languages=set(detected), run_id=self.run_id)
            fs, run = await self._run_one("codeql", sub)
            self.codeql_parts[group] = (fs, run)
            self._merge_codeql()
            return f"codeql {group}: {run.status.value}" + (f" ({run.reason})" if run.reason else "") + f"; combined: {self.runs['codeql'].status.value}"
        if action.name == "scan_declared":
            folder = action.target
            sub_repo = (self.repo / folder).resolve() if folder not in ("", ".") else self.repo
            self.declared_done.add(folder)
            sub = ScanContext(repo=sub_repo, work_dir=self.ctx.work_dir, languages=self.languages, run_id=self.run_id)
            fs, run = await self._run_one("osv-scanner", sub)
            prefix = "" if sub_repo == self.repo else sub_repo.relative_to(self.repo).as_posix() + "/"
            for f in fs:
                if f.file_path:
                    f.file_path = prefix + f.file_path
            have = {(f.rule_id, f.file_path, f.sink) for f in self.findings.get("osv-scanner", [])}
            self.findings.setdefault("osv-scanner", []).extend(f for f in fs if (f.rule_id, f.file_path, f.sink) not in have)
            osv = self.runs["osv-scanner"]
            osv.reason = f"the full run {osv.status.value}; declared versions of {folder or '.'} scanned separately: {run.status.value}"
            osv.findings_count = len(self.findings["osv-scanner"])
            return f"osv-scanner on {folder or '.'}: {run.status.value}, {len(fs)} finding(s) added"
        if action.name == "record_gap":
            gap = next(g for g in self._open_gaps() if g.startswith(action.target[:100]) or action.target in g)
            self.recorded_gaps.append(gap)
            return "gap recorded in the report (still open)"
        if action.name == "skip_with_reason":
            self.acknowledged[action.target] = action.why
            return f"{action.target} acknowledged as a hole"
        return "stopped"

    def _merge_codeql(self) -> None:
        groups = [g for g, (detected, _s) in CODEQL_LANGUAGES.items() if detected & self.languages]
        done = {g: p for g, p in self.codeql_parts.items()}
        findings = [f for fs, _r in done.values() for f in fs]
        ok = [g for g, (_fs, r) in done.items() if r.status is RunStatus.SUCCEEDED]
        failed = [g for g in done if g not in ok]
        run = self.runs["codeql"]
        complete = len(ok) == len(groups)
        run.status = RunStatus.SUCCEEDED if complete else RunStatus.FAILED
        run.reason = None if complete else ("per-language fallback: " + ", ".join(f"{g} {done[g][1].status.value}" for g in done)
                                            + (f"; not tried yet: {', '.join(g for g in groups if g not in done)}" if len(done) < len(groups) else ""))
        run.findings_count = len(findings)
        self.findings["codeql"] = findings

    # ---- the loop -------------------------------------------------------------------------------------------------------------------------------
    def result(self) -> ScanResult:
        if self._existing is not None:  # review mode: nothing ran, the scan is returned as it was
            return self._existing.model_copy(update={"coverage_gaps": list(self.gaps)})
        findings = [f for n in self.order for f in self.findings.get(n, [])]
        runs = [self.runs[n] for n in self.order if n in self.runs]
        return ScanResult(run_id=self.run_id, repo_path=str(self.repo), languages=sorted(self.languages),
                          findings=findings, runs=runs, coverage_gaps=list(self.gaps))

    async def run(self) -> OrchestrationResult:
        """Run the loop as a LangGraph graph (graphs/orchestrator_graph.py): plan -> execute_action -> update_state -> ... -> stop. The graph
        is the control flow; options, validation, budgets, the trail and the audit log stay in this class and in agent_loop."""
        final = await build_orchestrator_graph(self).ainvoke({}, {"recursion_limit": recursion_limit(self.cfg.max_steps)})
        return OrchestrationResult(self.result(), self.trail.entries, self.step, final["stop_reason"], final["goal_met"],
                                   list(self.recorded_gaps), dict(self.acknowledged))


async def orchestrate(repo: Path, tools: list[BaseTool] | None = None, *, policy: Policy | None = None, config: LoopConfig | None = None,
                      audit=None, skipped=(), scan_dir: Path | None = None) -> OrchestrationResult:
    """Scan `repo` with a bounded agent loop. `tools` default to the detection tools; nothing else can be run."""
    return await Orchestrator(repo, tools if tools is not None else default_tools(), policy=policy, config=config, audit=audit,
                              skipped=skipped, scan_dir=scan_dir).run()


async def review(result: ScanResult, *, policy: Policy | None = None, config: LoopConfig | None = None, audit=None, skipped=()) -> OrchestrationResult:
    """The same loop over a scan that already exists (a reused findings.json): no tool can run, so it only decides what to do with the
    coverage gaps and holes it finds, and says so in the trail."""
    return await Orchestrator(None, [], policy=policy, config=config, audit=audit, skipped=skipped, existing=result).run()
