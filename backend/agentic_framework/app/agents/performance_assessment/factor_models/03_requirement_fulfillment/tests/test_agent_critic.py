"""Run from 03_requirement_fulfillment with the backend environment:  python -m unittest discover -s tests -p "test_agent_critic.py"
The critic graph is driven by a scripted assessor and a scripted critic: flow, challenge and revision rules, what the critic is shown.
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments.agent import Agent  # noqa: E402
from experiments.agent_critic import CRITIC_MODEL, AgentCritic  # noqa: E402
from rf_bench.bench import build_manifest  # noqa: E402
from rf_bench.llm import Reply, ScriptedLLM  # noqa: E402
from rf_bench.runner import Usage  # noqa: E402
from rf_bench.scope import Scope  # noqa: E402

BENCH, MANIFEST = build_manifest(write=False)
TID = "S01-S1-SYN-001-T2"


class Recording(ScriptedLLM):
    def __init__(self, responder):
        super().__init__(responder)
        self.calls = []

    def chat(self, messages, **kw):
        self.calls.append({"model": kw.get("model"), "tag": kw.get("tag", ""), "messages": messages})
        return super().chat(messages, **{k: v for k, v in kw.items() if k != "model"})


def assessor(messages, tag):
    """A scripted assessor that finds code: searches for the deciding lines, then calls the criterion met and cites the first hit."""
    if ":map:" in tag:
        return '{"commits": []}'
    user = messages[-1]["content"]
    if "Observation 1" not in user:
        return json.dumps({"action": "search", "query": "seatsLeft|status"})
    seen = re.findall(r"^([0-9a-f]{10}) (\S+):(\d+): ", user, re.M)
    if seen:
        sha, path, line = seen[0]
        return json.dumps({"action": "verdict", "verdict": "met", "evidence": [{"sha": sha, "path": path, "lines": f"{line}-{line}"}], "reason": "found"})
    return json.dumps({"action": "verdict", "verdict": "not_met", "evidence": [], "reason": "none"})


def critic_says(assessments):
    def responder(messages, tag):
        if tag.startswith("critic"):
            n = len(re.findall(r"^C\d+: verdict", messages[-1]["content"], re.M))
            return json.dumps({"checks": [{"criterion": i + 1, "assessment": assessments.get(i + 1, "supported"),
                                           "suggested_verdict": "not_met", "objection": "the cited line sets another status"} for i in range(n)]})
        if "A reviewer questions" in messages[-1]["content"]:  # the revision: the assessor gives in
            return json.dumps({"action": "verdict", "verdict": "not_met", "evidence": [], "reason": "revised"})
        return assessor(messages, tag)
    return responder


def run(responder):
    t = BENCH.tasks[TID]
    scope = Scope(BENCH, t["sprint"], t["student"])
    llm = Recording(responder)
    out = AgentCritic().assess(BENCH, TID, scope, llm, Usage())
    return out, llm


class Critic(unittest.TestCase):
    def test_nothing_challenged_leaves_the_agents_verdicts(self):
        plain = Agent().assess(BENCH, TID, Scope(BENCH, "S01-S1", "SYN-001"), ScriptedLLM(assessor), Usage())
        out, llm = run(critic_says({}))
        self.assertEqual(out["verdicts"], plain["verdicts"])
        self.assertEqual(out["changes"], [])

    def test_a_challenged_verdict_is_revised_once(self):
        out, llm = run(critic_says({1: "overstated"}))
        self.assertEqual(out["verdicts"][0], "not_met")
        self.assertEqual([c["criterion"] for c in out["changes"]], [1])
        revisions = [c for c in llm.calls if "A reviewer questions" in c["messages"][-1]["content"]]
        self.assertEqual(len(revisions), 1)

    def test_the_critic_uses_another_model_and_only_it(self):
        out, llm = run(critic_says({}))
        critic_calls = [c for c in llm.calls if c["tag"].startswith("critic")]
        self.assertEqual(len(critic_calls), 1)
        self.assertEqual(critic_calls[0]["model"], CRITIC_MODEL)
        self.assertTrue(all(c["model"] is None for c in llm.calls if not c["tag"].startswith("critic")))

    def test_the_critic_sees_cited_lines_not_the_rating_or_other_code(self):
        out, llm = run(critic_says({}))
        prompt = [c for c in llm.calls if c["tag"].startswith("critic")][0]["messages"][-1]["content"]
        self.assertNotIn("RF_", prompt)
        self.assertNotIn("rating", prompt.lower())
        cited_lines = re.findall(r"^\w{10} \S+:(\d+): (.*)$", prompt, re.M)
        self.assertLessEqual(len(cited_lines), 25 * len(BENCH.tasks[TID]["criteria"]))

    def test_a_failed_critic_changes_nothing(self):
        def broken(messages, tag):
            return "no json" if tag.startswith("critic") else assessor(messages, tag)
        plain = Agent().assess(BENCH, TID, Scope(BENCH, "S01-S1", "SYN-001"), ScriptedLLM(assessor), Usage())
        out, llm = run(broken)
        self.assertEqual(out["verdicts"], plain["verdicts"])

    def test_revision_cannot_loop(self):
        def always_challenge(messages, tag):
            if tag.startswith("critic"):
                n = len(re.findall(r"^C\d+: verdict", messages[-1]["content"], re.M))
                return json.dumps({"checks": [{"criterion": i + 1, "assessment": "overstated", "suggested_verdict": "not_met", "objection": "x"} for i in range(n)]})
            if "A reviewer questions" in messages[-1]["content"]:
                return '{"action": "search", "query": "zzz"}'  # never gives a verdict: the budget forces one
            return assessor(messages, tag)
        out, llm = run(always_challenge)
        n = len(BENCH.tasks[TID]["criteria"])
        self.assertEqual(len(out["verdicts"]), n)
        self.assertLessEqual(len(llm.calls), 1 + n * 4 + 1 + n * 2)


if __name__ == "__main__":
    unittest.main()
