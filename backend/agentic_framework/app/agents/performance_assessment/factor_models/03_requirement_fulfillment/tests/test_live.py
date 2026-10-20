"""Run from factor_models/:  python -m unittest discover -s 03_requirement_fulfillment/tests -p "test_live.py"   (needs langgraph)

The Requirement Fulfillment sub-agent on real evidence: the evidence-backed bench, the student-only rule, the evaluator with a scripted language model.
"""
import importlib.util
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
RF = HERE.parents[1]
sys.path.insert(0, str(RF.parent))
sys.path.insert(0, str(RF))

from evidence.testing import commit, evidence, file  # noqa: E402
from rf_bench.llm import ScriptedLLM  # noqa: E402
from rf_live import EvidenceBench  # noqa: E402

spec = importlib.util.spec_from_file_location("rf_evaluate_test", RF / "evaluate.py")
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)

SHA = "a" * 40
PATCH = "@@ -0,0 +1,4 @@\n+passwords = bcrypt.hashpw(raw)\n+# a comment that is not work\n+def register(email):\n+    return duplicate_emails_rejected(email)\n"


def case(status="Done", provisional=False, extra_tasks=()):
    c = commit(SHA, "2026-02-03T10:00:00+05:30", [file("src/auth.py", code=3, comment=1)], subject="register users")
    c["files"][0]["kind"] = "code"
    tasks = [{"id": "T1", "title": "Registration", "description": "Users can register", "acceptance_criteria": ["Passwords are hashed with bcrypt", "Duplicate emails are rejected"], "story_points": 3,
              "subtask_count": 2, "assignee": "STU-001", "status": status, "completed_by": "STU-001", "commit_ids": [SHA]}, *extra_tasks]
    ev = evidence([c], tasks=tasks, **({"as_of": "2026-02-08T00:00:00Z"} if provisional else {}))
    return {"evidence": ev, "patches": {SHA: {"src/auth.py": PATCH}}}


def scripted():
    from experiments.agent_critic import AgentCritic
    return ScriptedLLM(AgentCritic.dry_responder)


class Bench(unittest.TestCase):
    def test_commits_tasks_and_cleaned_hunks_come_from_the_evidence(self):
        p = case()
        b = EvidenceBench(p["evidence"], p["patches"])
        self.assertEqual([c["sha"] for c in b.student_commits("T01-S1", "STU-001")], [SHA])
        self.assertEqual(b.tasks_of("T01-S1", "STU-001"), ["T1"])
        self.assertEqual(b.task_public("T1")["criteria"][0], "Passwords are hashed with bcrypt")
        hunk = b.hunk(SHA, "src/auth.py")
        self.assertTrue(all(h[:1] in "+-" for h in hunk))
        self.assertFalse(any("a comment that is not work" in h for h in hunk))  # comment lines are cleaned away
        self.assertTrue(any("bcrypt" in h for h in hunk))

    def test_nothing_is_visible_for_another_student_or_sprint(self):
        p = case()
        b = EvidenceBench(p["evidence"], p["patches"])
        self.assertEqual(b.student_commits("T01-S1", "STU-002"), [])
        self.assertEqual(b.tasks_of("T01-S1", "STU-002"), [])

    def test_a_task_that_was_not_started_is_not_sent_to_the_model(self):
        p = case(extra_tasks=[{"id": "T2", "title": "x", "acceptance_criteria": ["y"], "assignee": "STU-001", "status": "To Do", "commit_ids": []}])
        b = EvidenceBench(p["evidence"], p["patches"])
        self.assertTrue(b.should_judge("T1") and not b.should_judge("T2"))
        self.assertFalse(b.should_judge("T1", provisional=False) is False)


class MapsCommits(unittest.TestCase):
    def test_the_agent_can_pick_a_commit_and_read_its_files(self):
        """Regression: the first step of the agent reads bench.commits[sha]; a run on real evidence stopped there with 'no attribute commits'."""
        import json
        from experiments.agent_critic import AgentCritic

        def responder(messages, tag):
            if tag.startswith("agent:map"):
                return json.dumps({"commits": [SHA]})
            return AgentCritic.dry_responder(messages, tag)

        p = case()
        self.assertEqual(EvidenceBench(p["evidence"], p["patches"]).commits[SHA]["files"][0]["path"], "src/auth.py")
        r = E.evaluate(p, {"llm": ScriptedLLM(responder)})
        self.assertEqual(r["tasks"][0]["status"], "judged")
        self.assertIsNone(r["tasks"][0].get("error"))


class NothingToShow(unittest.TestCase):
    """A task whose student has no changed lines the model could be shown must not cost a model call or become a made-up verdict."""

    def test_provisional_with_no_visible_change_is_not_available_not_zero(self):
        p = case(provisional=True)
        p["evidence"]["commits"] = []
        llm = scripted()
        with self.assertRaises(E.NotEnoughEvidence):
            E.evaluate(p, {"llm": llm})
        self.assertEqual(llm.n, 0)

    def test_final_with_no_visible_change_counts_zero_without_calling_the_model(self):
        p = case()
        p["evidence"]["commits"] = []
        llm = scripted()
        r = E.evaluate(p, {"llm": llm})
        self.assertEqual(llm.n, 0)
        self.assertEqual(r["tasks"][0]["status"], "no_visible_change")
        self.assertEqual(r["score"], 0.0)
        self.assertTrue(any("not sent to the model" in w for w in r["warnings"]))

    def test_configuration_files_are_shown_to_the_model(self):
        c = commit(SHA, "2026-02-03T10:00:00+05:30", [file("k8s/auth-deployment.yaml", code=12)], subject="deploy auth")
        ev = evidence([c], tasks=[{"id": "T1", "title": "Deploy", "description": "", "acceptance_criteria": ["The service has a deployment manifest"], "story_points": 3, "subtask_count": 1,
                                   "assignee": "STU-001", "status": "Done", "completed_by": "STU-001", "commit_ids": [SHA]}])
        b = EvidenceBench(ev, {SHA: {"k8s/auth-deployment.yaml": "@@ -0,0 +1,2 @@" + chr(10) + "+kind: Deployment" + chr(10) + "+name: auth" + chr(10)}})
        self.assertEqual(b.commits[SHA]["files"][0]["path"], "k8s/auth-deployment.yaml")
        self.assertTrue(any("kind: Deployment" in h for h in b.hunk(SHA, "k8s/auth-deployment.yaml")))

    def test_a_cancelled_run_stops_between_tasks(self):
        import threading
        stop = threading.Event()
        stop.set()
        extra = {"id": "T2", "title": "x", "acceptance_criteria": ["y"], "assignee": "STU-001", "status": "Done", "commit_ids": [SHA]}
        with self.assertRaises(E.NotEnoughEvidence):
            E.evaluate(case(extra_tasks=[extra]), {"llm": scripted(), "cancel": stop})


class VerdictsAreReusedWhenNothingChanged(unittest.TestCase):
    """A nightly snapshot of a quiet team, a re-run or a re-composition must not pay the model again for a task whose evidence did not change."""

    def setUp(self):
        import tempfile
        self.dir = tempfile.TemporaryDirectory()
        self.old = os.environ.get("RF_CACHE_DIR")
        os.environ["RF_CACHE_DIR"] = self.dir.name

    def tearDown(self):
        if self.old is None:
            os.environ.pop("RF_CACHE_DIR", None)
        else:
            os.environ["RF_CACHE_DIR"] = self.old
        self.dir.cleanup()

    def test_the_second_run_makes_no_model_call_and_gives_the_same_answer(self):
        first, second = scripted(), scripted()
        a = E.evaluate(case(), {"llm": first})
        b = E.evaluate(case(), {"llm": second})
        self.assertGreater(first.n, 0)
        self.assertEqual(second.n, 0)
        self.assertEqual(a["score"], b["score"])
        self.assertEqual(a["tasks"][0]["verdicts"], b["tasks"][0]["verdicts"])
        self.assertEqual((a["features"]["RF_tasks_reused"], b["features"]["RF_tasks_reused"]), (0, 1))

    def test_a_change_in_the_students_lines_judges_the_task_again(self):
        E.evaluate(case(), {"llm": scripted()})
        changed = case()
        changed["patches"][SHA]["src/auth.py"] += "+def extra():" + chr(10) + "+    return 1" + chr(10)
        again = scripted()
        E.evaluate(changed, {"llm": again})
        self.assertGreater(again.n, 0)

    def test_a_change_in_the_acceptance_criteria_judges_the_task_again(self):
        E.evaluate(case(), {"llm": scripted()})
        changed = case()
        changed["evidence"]["tasks"][0]["acceptance_criteria"] = ["Passwords are hashed with bcrypt", "Duplicate emails are rejected", "A welcome mail is sent"]
        again = scripted()
        E.evaluate(changed, {"llm": again})
        self.assertGreater(again.n, 0)

    def test_it_can_be_switched_off(self):
        os.environ["RF_CACHE"] = "0"
        try:
            E.evaluate(case(), {"llm": scripted()})
            again = scripted()
            E.evaluate(case(), {"llm": again})
            self.assertGreater(again.n, 0)
        finally:
            os.environ.pop("RF_CACHE", None)

    def test_an_unclear_verdict_is_never_kept(self):
        E._cache_put("k" * 64, {"verdicts": ["met", "cannot_tell"]})
        E._cache_put("e" * 64, {"error": "refused", "verdicts": ["met"]})
        self.assertIsNone(E._cache_get("k" * 64))
        self.assertIsNone(E._cache_get("e" * 64))


class ModelCallsThatTheProviderRefuses(unittest.TestCase):
    def test_a_call_to_a_tool_that_is_not_offered_costs_a_step_not_the_task(self):
        """The provider answers HTTP 400 'Tool call validation failed' when the model names a tool that is not offered (in the last step only the verdict is). It happened nine times in a real run."""
        from experiments import agent as agent_mod
        from rf_bench.llm import Reply
        from rf_bench.runner import Usage

        class Refusing:
            model = "m"

            def chat(self, messages, **kw):
                return Reply(error="HTTP 400: Tool call validation failed: attempted to call tool read_hunk which was not in request.tools", error_kind="bad_request", attempts=1)

        out = agent_mod._call_action({"usage": Usage(), "llm": Refusing(), "run": 0}, [{"role": "user", "content": "x"}], [], "t")
        self.assertEqual(out["action"], "invalid")
        self.assertNotIn("error", out)


class Evaluate(unittest.TestCase):
    def test_score_comes_from_verdicts_by_plain_arithmetic(self):
        r = E.evaluate(case(), {"llm": scripted(), "rf_critic": True})
        self.assertEqual(r["factor"], "requirement_fulfillment")
        self.assertEqual(r["features"]["RF_tasks_judged"], 1)
        t = r["tasks"][0]
        self.assertEqual(t["status"], "judged")
        self.assertAlmostEqual(r["score"], sum({"met": 1.0, "partly": 0.5}.get(v, 0.0) for v in t["verdicts"]) / len(t["verdicts"]), places=4)
        self.assertTrue(0.0 <= r["interval"][0] <= r["score"] <= r["interval"][1] <= 1.0)

    def test_unstarted_tasks_count_as_zero_without_a_model_call(self):
        extra = {"id": "T2", "title": "x", "acceptance_criteria": ["y"], "assignee": "STU-001", "status": "To Do", "commit_ids": []}
        llm = scripted()
        r = E.evaluate(case(extra_tasks=[extra]), {"llm": llm})
        rows = {t["task"]: t for t in r["tasks"]}
        self.assertEqual(rows["T2"]["status"], "not_started")
        self.assertEqual(rows["T2"]["fulfilment"], 0.0)
        self.assertAlmostEqual(r["score"], rows["T1"]["fulfilment"] / 2, places=4)

    def test_provisional_mode_judges_only_done_or_in_review_tasks(self):
        extra = {"id": "T2", "title": "x", "acceptance_criteria": ["y"], "assignee": "STU-001", "status": "In Progress", "commit_ids": [SHA]}
        r = E.evaluate(case(provisional=True, extra_tasks=[extra]), {"llm": scripted()})
        self.assertTrue(r["provisional"] and {t["task"] for t in r["tasks"] if t["status"] == "judged"} == {"T1"})
        self.assertTrue(any("provisional" in w for w in r["warnings"]))
        with self.assertRaises(E.NotEnoughEvidence):
            E.evaluate(case(status="In Progress", provisional=True), {"llm": scripted()})

    def test_progress_events_are_reported(self):
        seen = []
        E.evaluate(case(), {"llm": scripted(), "on_event": lambda t, m, p: seen.append(t)})
        self.assertEqual([seen[0], seen[-1]], ["task_start", "task_done"])
        self.assertTrue(all(k == "llm_call" for k in seen[1:-1]) and len(seen) > 2)  # every model call is reported between them

    def test_without_a_language_model_the_score_is_not_available(self):
        old = {k: os.environ.pop(k, None) for k in ("GROQ_API_KEYS", "RF_ENV_FILE")}
        try:
            with self.assertRaises(E.NotEnoughEvidence):
                E.evaluate(case())
        finally:
            for k, v in old.items():
                if v is not None:
                    os.environ[k] = v

    def test_no_tasks_with_criteria_is_not_available(self):
        p = case()
        p["evidence"]["tasks"] = []
        with self.assertRaises(E.NotEnoughEvidence):
            E.evaluate(p, {"llm": scripted()})


if __name__ == "__main__":
    unittest.main()
