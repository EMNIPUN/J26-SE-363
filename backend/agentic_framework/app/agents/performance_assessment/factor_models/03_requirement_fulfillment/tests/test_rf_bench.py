"""Run from 03_requirement_fulfillment:  python -m unittest discover -s tests -p "test_rf_bench.py"

Covers the shared benchmark, the student-only tools (the leak tests of plan.md, section 3), the scorer and the rubric parser.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rf_bench import metrics  # noqa: E402
from rf_bench.bench import Bench, build_manifest, load_manifest  # noqa: E402
from rf_bench.rubric import parse_verdicts  # noqa: E402
from rf_bench.schema import band, bucket_of, sprint_score, task_fulfilment  # noqa: E402
from rf_bench.scope import Scope  # noqa: E402

BENCH, MANIFEST = build_manifest(write=False)


class Benchmark(unittest.TestCase):
    def test_matches_the_frozen_manifest(self):
        self.assertEqual(load_manifest()["sha256"], MANIFEST["sha256"])

    def test_every_task_has_truth_for_each_criterion(self):
        for t in BENCH.tasks.values():
            self.assertEqual(len(t["criteria"]), len(t["truth"]["credited"]))
            self.assertTrue(all(x in (0, 1) for x in t["truth"]["credited"]))

    def test_work_finished_by_a_teammate_is_not_credited(self):
        mates = [t for t in BENCH.tasks.values() if t["completed_by_teammate"]]
        self.assertTrue(mates)
        for t in mates:
            self.assertEqual(sum(t["truth"]["credited"]), 0)
            self.assertFalse(BENCH.task_commits(t["id"]))  # the assignee has no commit for it

    def test_split_is_student_disjoint(self):
        self.assertFalse(set(MANIFEST["dev_students"]) & set(MANIFEST["held_out_students"]))
        for m in MANIFEST["tasks"].values():
            self.assertEqual(m["split"] == "dev", m["student"] in MANIFEST["dev_students"])

    def test_sizes_follow_the_real_distribution(self):
        lines = sorted(m["lines"] for m in MANIFEST["tasks"].values() if m["lines"])
        med, p90 = lines[len(lines) // 2], lines[int(0.9 * len(lines))]
        self.assertTrue(600 < med < 1100, med)
        self.assertTrue(2400 < p90 < 4200, p90)
        buckets = {m["bucket"] for m in MANIFEST["tasks"].values()}
        self.assertEqual(len(buckets), 5)

    def test_the_status_of_a_task_is_never_shown(self):
        s = Scope(BENCH, "S01-S1", "SYN-001")
        self.assertNotIn("Done", s.my_tasks())
        self.assertNotIn("Partially", s.my_tasks())

    def test_deciding_code_is_in_the_authors_commits(self):
        tid = "S01-S1-SYN-001-T2"
        diff = BENCH.task_diff(tid)
        self.assertIn("seatsLeft", diff)
        self.assertIn("status(400)", diff)


class StudentOnlyAccess(unittest.TestCase):
    """Every tool is tried on a teammate's data and must fail to return it."""

    def setUp(self):
        self.me = Scope(BENCH, "S01-S1", "SYN-001")
        mine = self.me.own_shas()
        self.teammate_commits = [c for c in BENCH.commits.values() if c["sprint"] == "S01-S1" and c["author"] != "SYN-001"]
        self.assertTrue(self.teammate_commits and mine)

    def test_list_commits_has_no_teammate_commit(self):
        text = self.me.list_commits()
        for c in self.teammate_commits:
            self.assertNotIn(c["sha"], text)

    def test_reading_a_teammates_commit_by_id_fails(self):
        c = self.teammate_commits[0]
        f = c["files"][0]["path"] if c["files"] else "x"
        self.assertIn("unknown", self.me.read_hunk(c["sha"], f))
        self.assertIn("unknown", self.me.list_changes(c["sha"]))
        self.assertEqual(len(self.me.seen), 0)

    def test_search_never_returns_a_teammates_line(self):
        owner = [(k, v) for k, v in BENCH.place.items() if BENCH.commits[k[0]]["author"] != "SYN-001" and BENCH.commits[k[0]]["sprint"] == "S01-S1"]
        self.assertTrue(owner)
        (sha, path), v = owner[0]
        needle = max(v["lines"], key=len).strip()[:30]
        result = self.me.search_changes(needle)
        self.assertNotIn(sha, result)

    def test_search_falls_back_to_the_words_of_the_query(self):
        out = self.me.search_changes("seats left capacity")
        self.assertTrue("seatsLeft" in out or "capacity" in out.lower())
        self.assertIn("no exact match", out)
        self.assertIn("no match", self.me.search_changes("zzzqqq"))

    def test_my_tasks_has_only_my_tasks(self):
        text = self.me.my_tasks()
        self.assertIn("S01-S1-SYN-001-T1", text)
        self.assertNotIn("SYN-002-T", text)

    def test_commit_hints_refuse_a_teammates_task(self):
        self.assertIn("unknown task", self.me.task_commit_hints("S01-S1-SYN-002-T1"))

    def test_a_task_finished_by_a_teammate_shows_no_code_for_the_assignee(self):
        s = Scope(BENCH, "S01-S1", "SYN-004")
        self.assertIn("[completed by a teammate]", s.my_tasks())
        self.assertIn("no commit message names this task", s.task_commit_hints("S01-S1-SYN-004-T1"))

    def test_coverage_counts_only_what_was_read(self):
        c = next(iter(self.me.own_shas()))
        f = BENCH.commits[c]["files"][0]["path"]
        before = self.me.coverage()
        self.me.read_hunk(c, f, 0, 20)
        self.assertGreater(self.me.coverage(), before)
        self.assertLessEqual(self.me.coverage(), 1.0)

    def test_read_is_size_capped(self):
        big = next(c for c in BENCH.commits.values() if c["files"] and c["files"][0]["added"] > 300)
        scope = Scope(BENCH, big["sprint"], big["author"])
        out = scope.read_hunk(big["sha"], big["files"][0]["path"], 0, 100000)
        self.assertLessEqual(out.count("\n"), 130)
        self.assertIn("continue with start=", out)


class Scoring(unittest.TestCase):
    def test_rating_rule(self):
        self.assertEqual(task_fulfilment(["met", "met", "not_met"]), 2 / 3)
        self.assertEqual(task_fulfilment(["partly", "partly"]), 0.5)
        self.assertEqual(task_fulfilment(["cannot_tell"]), 0.0)
        self.assertEqual(band(0.0), 1)
        self.assertEqual(band(1.0), 5)
        self.assertEqual(sprint_score([1.0, 0.0]), 0.5)
        self.assertEqual(bucket_of(3999), "<=4k")
        self.assertEqual(bucket_of(40000), ">32k")

    def test_metrics_on_known_values(self):
        a, b = [0, 0.5, 1, 0.25], [0, 0.5, 1, 0.25]
        self.assertAlmostEqual(metrics.pearson(a, b), 1.0)
        self.assertAlmostEqual(metrics.spearman(a, b), 1.0)
        self.assertAlmostEqual(metrics.weighted_kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]), 1.0)
        self.assertLess(metrics.weighted_kappa([1, 1, 5, 5], [5, 5, 1, 1]), 0)
        ag = metrics.agreement([0.0, 1.0], [0.5, 0.5])
        self.assertAlmostEqual(ag["MAE"], 0.5)

    def test_a_perfect_experiment_scores_perfectly_and_a_failure_scores_as_no_credit(self):
        tids = [t for t in MANIFEST["tasks"] if MANIFEST["tasks"][t]["verifiable"]][:30]
        def verdicts(tid):
            return ["met" if x else "not_met" for x in BENCH.tasks[tid]["truth"]["credited"]]
        results = [{"task_id": t, "run": 0, "verdicts": verdicts(t), "usage": {"total_tokens": 10, "calls": 1, "seconds": 0.1}} for t in tids]
        sc = metrics.score(metrics.task_rows(results, BENCH, MANIFEST))
        self.assertEqual(sc["failure_rate"], 0)
        self.assertAlmostEqual(sc["completed_only"]["task"]["MAE"], 0.0)
        self.assertAlmostEqual(sc["completed_only"]["criterion"]["accuracy"], 1.0)
        results[0] = {"task_id": tids[0], "run": 0, "error": "too large", "error_kind": "too_large", "usage": {}}
        sc = metrics.score(metrics.task_rows(results, BENCH, MANIFEST))
        self.assertAlmostEqual(sc["failure_rate"], 1 / 30)

    def test_repeatability_of_identical_runs(self):
        rows = [{"task_id": f"t{i}", "failed": False, "pred_rf": v, "truth_rf": v, "run": k} for i, v in enumerate([0.1, 0.5, 0.9, 0.3]) for k in range(3)]
        r = metrics.repeatability(rows)
        self.assertEqual(r["mean_sd"], 0.0)
        self.assertEqual(r["share_moving_a_band"], 0.0)


class Pacing(unittest.TestCase):
    def setUp(self):
        import tempfile
        from rf_bench import llm
        self._saved = llm.USAGE_FILE
        llm.USAGE_FILE = Path(tempfile.mkdtemp()) / "usage.json"  # the tests must not read or write the real daily counters

    def tearDown(self):
        from rf_bench import llm
        llm.USAGE_FILE = self._saved

    def test_per_minute_limit_is_respected_across_keys(self):
        from rf_bench.llm import GroqPool
        pool = GroqPool(model="m", keys=["a", "b"], tpm=8000)
        picks = [pool._pick(5000) for _ in range(3)]
        self.assertEqual([w for _, w in picks[:2]], [0.0, 0.0])      # one request per key fits in the minute
        self.assertGreater(picks[2][1], 30)                           # the third must wait for a window
        self.assertEqual(pool._pick(9000)[1], 0.0)                    # too large for any window: sent, the service's refusal is the finding

    def test_a_random_organisation_id_is_not_a_daily_quota(self):
        import re
        msg = "Rate limit reached for model x in organization org_01tpdrpdabc service tier on_demand on tokens per minute (TPM): Limit 8000"
        low = re.sub(r"org_\w+", "org", msg).lower()
        self.assertFalse(re.search(r"per day|\(tpd\)|\(rpd\)", low))
        self.assertTrue(re.search(r"per day|\(tpd\)|\(rpd\)", "on tokens per day (TPD): Limit 200000".lower()))

    def test_wait_hint_is_parsed(self):
        from rf_bench.llm import parse_wait
        self.assertAlmostEqual(parse_wait("Please try again in 10m46.27s. Need"), 646.77, places=1)
        self.assertAlmostEqual(parse_wait("try again in 1h2m3s"), 3723.5, places=1)
        self.assertAlmostEqual(parse_wait("try again in 850ms"), 1.35, places=2)
        self.assertEqual(parse_wait("no hint", default=8.0), 8.0)

    def test_at_the_daily_limit_the_pool_waits_for_the_refill_when_asked(self):
        import os
        from rf_bench import llm
        from rf_bench.llm import GroqPool, Reply
        calls = {"n": 0}

        def fake_call(self, key, body):
            calls["n"] += 1
            if calls["n"] <= 2:  # both keys are refused once
                return Reply(error="HTTP 429: tokens per day (TPD)", error_kind="quota", meta={"retry_after": 0.1})
            return Reply(text="ok", model="m")
        saved = GroqPool._call
        GroqPool._call = fake_call
        os.environ["RF_WAIT"] = "1"
        try:
            pool = GroqPool(model="m", keys=["a", "b"], tpm=8000)
            r = pool.chat([{"role": "user", "content": "hi"}], max_tokens=10)
            self.assertTrue(r.ok)
            self.assertEqual(calls["n"], 3)
            os.environ["RF_WAIT"] = "0"
            calls["n"] = 0
            pool2 = GroqPool(model="m", keys=["a", "b"], tpm=8000)
            r2 = pool2.chat([{"role": "user", "content": "hi"}], max_tokens=10)
            self.assertEqual(r2.error_kind, "quota")  # without the wait mode it is returned, not hidden
        finally:
            GroqPool._call = saved
            os.environ.pop("RF_WAIT", None)

    def test_keys_are_not_in_the_repr_or_state(self):
        from rf_bench.llm import GroqPool
        pool = GroqPool(model="m", keys=["gsk_secretvalue"], tpm=8000)
        self.assertNotIn("gsk_secretvalue", json.dumps(pool.daily))


class Runner(unittest.TestCase):
    def test_a_daily_quota_pauses_the_run_and_records_nothing(self):
        import argparse
        import shutil
        import types
        from rf_bench import runner

        class Exp:
            name = "fake"
            dry_responder = staticmethod(lambda m, t: "{}")

            def config(self):
                return {}

            def assess(self, bench, tid, scope, llm, usage, run=0):
                usage.failures.append("quota")
                return {"error": "every key is exhausted for today", "error_kind": "quota"}
        mod = types.ModuleType("fake_exp")
        mod.Exp = Exp
        sys.modules["fake_exp"] = mod
        out = ".runs/test_pause"
        shutil.rmtree(runner.RF / out, ignore_errors=True)
        runner.cmd_run(argparse.Namespace(exp="fake_exp:Exp", split="dev", per_bucket=1, runs=1, out=out, workers=2, model=None, fallback=None, effort="low", dry=True))
        res = runner.RF / out / "results.jsonl"
        self.assertTrue(not res.exists() or res.read_text(encoding="utf-8").strip() == "")
        shutil.rmtree(runner.RF / out, ignore_errors=True)


class Rubric(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_verdicts('{"verdicts": ["met", "Not Met", "partial"]}', 3), ["met", "not_met", "partly"])
        self.assertIsNone(parse_verdicts('{"verdicts": ["met"]}', 2))
        self.assertIsNone(parse_verdicts("no json", 1))
        self.assertIsNone(parse_verdicts('{"verdicts": ["maybe"]}', 1))
        self.assertEqual(parse_verdicts('text before {"verdicts": ["met"]} after', 1), ["met"])


if __name__ == "__main__":
    unittest.main()
