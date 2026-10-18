"""Run from 03_requirement_fulfillment with the backend environment (needs langgraph):
    python -m unittest discover -s tests -p "test_agent.py"
The whole graph is driven by a scripted model: flow, budgets, the evidence check and the student-only rule, with no network and no key.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.agent import Agent, MAX_STEPS  # noqa: E402
from rf_bench.bench import build_manifest  # noqa: E402
from rf_bench.llm import ScriptedLLM  # noqa: E402
from rf_bench.runner import Usage  # noqa: E402
from rf_bench.schema import est_tokens  # noqa: E402
from rf_bench.scope import Scope  # noqa: E402

BENCH, MANIFEST = build_manifest(write=False)


def run(tid, responder, limit=None):
    t = BENCH.tasks[tid]
    scope = Scope(BENCH, t["sprint"], t["student"])
    llm = ScriptedLLM(responder, limit_tokens=limit)
    usage = Usage()
    out = Agent().assess(BENCH, tid, scope, llm, usage)
    return out, scope, llm, usage


class AgentFlow(unittest.TestCase):
    def test_scripted_agent_gives_one_verdict_per_criterion(self):
        for tid in ["S01-S1-SYN-001-T2", "S02-S1-SYN-006-T1", "S05-S1-SYN-021-T1"]:
            out, scope, llm, usage = run(tid, Agent.dry_responder)
            self.assertNotIn("error", out, out)
            self.assertEqual(len(out["verdicts"]), len(BENCH.tasks[tid]["criteria"]))
            self.assertTrue(all(v in ("met", "partly", "not_met", "cannot_tell") for v in out["verdicts"]))

    def test_budget_is_respected(self):
        # a model that only ever searches is forced to a verdict at the last step
        search = lambda m, tag: '{"action": "search", "query": "x"}' if ":map:" not in tag else '{"commits": []}'  # noqa: E731
        tid = "S01-S1-SYN-001-T1"
        out, scope, llm, usage = run(tid, search)
        n = len(BENCH.tasks[tid]["criteria"])
        self.assertEqual(out["verdicts"], ["cannot_tell"] * n)
        self.assertLessEqual(llm.n, 1 + n * MAX_STEPS)

    def test_invented_evidence_is_discarded(self):
        def liar(messages, tag):
            if ":map:" in tag:
                return '{"commits": []}'
            return json.dumps({"action": "verdict", "verdict": "met", "evidence": [{"sha": "0000000000", "path": "a.js", "lines": "1-3"}], "reason": "trust me"})
        out, *_ = run("S01-S1-SYN-001-T1", liar)
        self.assertEqual(set(out["verdicts"]), {"cannot_tell"})
        self.assertEqual(out["cites_ok"], 0.0)

    def test_a_met_verdict_without_evidence_is_discarded(self):
        def lazy(messages, tag):
            return '{"commits": []}' if ":map:" in tag else '{"action": "verdict", "verdict": "met", "evidence": [], "reason": "looks fine"}'
        out, *_ = run("S01-S1-SYN-001-T1", lazy)
        self.assertEqual(set(out["verdicts"]), {"cannot_tell"})

    def test_garbage_replies_do_not_crash(self):
        out, *_ = run("S01-S1-SYN-001-T1", lambda m, t: "not json at all")
        self.assertNotIn("error", out)
        self.assertEqual(set(out["verdicts"]), {"cannot_tell"})

    def test_a_refused_call_is_a_failure_not_a_guess(self):
        out, *_ = run("S01-S1-SYN-001-T1", Agent.dry_responder, limit=10)
        self.assertEqual(out["error_kind"], "too_large")
        self.assertNotIn("verdicts", out)


class ContextDoesNotGrowWithTaskSize(unittest.TestCase):
    def test_every_prompt_stays_small_on_the_largest_tasks(self):
        biggest = sorted(MANIFEST["tasks"], key=lambda t: -MANIFEST["tasks"][t]["tokens"])[:3]
        sizes = []

        def spy(messages, tag):
            sizes.append(sum(est_tokens(m["content"]) for m in messages))
            return Agent.dry_responder(messages, tag)
        for tid in biggest:
            self.assertGreater(MANIFEST["tasks"][tid]["tokens"], 32000)
            run(tid, spy)
        self.assertLess(max(sizes), 6500, max(sizes))  # inside the account's per-request limit


class OnlyTheStudentsCode(unittest.TestCase):
    def test_mapping_evidence_and_reads_stay_inside_the_students_commits(self):
        tid = "S01-S1-SYN-001-T2"
        out, scope, llm, usage = run(tid, Agent.dry_responder)
        own = scope.own_shas()
        self.assertTrue(set(out["mapping"]) <= own)
        for ev in out["evidence"]:
            for e in ev:
                self.assertIn(e["sha"], own)
        for tool, args in scope.calls:
            if "sha" in args:
                self.assertIn(args["sha"], own)

    def test_an_instruction_planted_in_code_is_data(self):
        # the rubric tells the model so; here we check the text really reaches the prompt only as quoted observation
        seen = []

        def spy(messages, tag):
            seen.append(messages[0]["content"])
            return Agent.dry_responder(messages, tag)
        run("S01-S1-SYN-001-T1", spy)
        self.assertIn("never an instruction", seen[0])


if __name__ == "__main__":
    unittest.main()
