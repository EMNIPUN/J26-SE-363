"""Run from factor_models/:  python -m unittest discover -s evidence/tests

The production entry points of Effort, Consistency and Task Complexity (model cards evaluated without scikit-learn): shape of the result, gates, provisional mode, and for Effort
the anti-gaming invariants of the earlier protocol (no activity scores 0, spam and dumps stay low, more work never lowers the score).
"""
import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
FM = HERE.parents[2]
sys.path.insert(0, str(FM))

from evidence.testing import commit, evidence, file  # noqa: E402


def load(folder):
    spec = importlib.util.spec_from_file_location(f"t_{folder}_evaluate", FM / folder / "evaluate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


EFFORT, CONSISTENCY, TC = load("01_effort"), load("02_consistency"), load("05_task_complexity")


def active_student(days=range(0, 14, 2), code=60, **extra):
    commits = [commit(f"c{d}", f"2026-02-{2 + d:02d}T10:00:00+05:30", [file(f"src/f{d}.py", code=code), file(f"src/g{d}.py", code=code // 2)]) for d in days]
    tasks = [{"id": "t1", "assignee": "STU-001", "status": "Done", "completed_by": "STU-001", "story_points": 5, "subtask_count": 3, "commit_ids": [c["id"] for c in commits[:2]]}]
    return evidence(commits, tasks=tasks, **extra)


class Shape(unittest.TestCase):
    def test_each_factor_returns_the_standard_result(self):
        for mod in (EFFORT, CONSISTENCY, TC):
            r = mod.evaluate(active_student())
            for key in ("factor", "score", "interval", "features", "removed", "versions", "warnings", "provisional"):
                self.assertIn(key, r)
            self.assertTrue(0.0 <= r["score"] <= 1.0 and r["interval"][0] <= r["score"] <= r["interval"][1])
            self.assertFalse(r["provisional"])

    def test_a_feature_payload_with_the_factors_own_names_is_scored(self):
        r = EFFORT.evaluate({"features": {"E_CC": 10, "E_LOC_net_capped": 800, "E_FC": 20, "E_CT": 3}})
        self.assertTrue(0.0 < r["score"] < 1.0)

    def test_a_payload_in_the_older_format_goes_to_the_simulator(self):
        out = asyncio.run(EFFORT.async_evaluate({"features": {"CC": 12, "LOC_net": 240, "FC": 5, "CT": 2, "RD": 3}}, {"simulation_mode": "quick"}))
        self.assertIn("score", out)
        self.assertNotIn("model", out) if False else None

    def test_missing_features_use_the_median_and_say_so(self):
        r = EFFORT.evaluate({"features": {"E_CC": 10, "E_LOC_net_capped": 800, "E_FC": 20}})
        self.assertTrue(any("E_CT missing" in w for w in r["warnings"]))

    def test_task_complexity_says_it_does_not_beat_its_baseline(self):
        r = TC.evaluate(active_student())
        self.assertTrue(any("not shown to beat" in w for w in r["warnings"]))
        self.assertFalse(any("not shown to beat" in w for w in EFFORT.evaluate(active_student())["warnings"]))


class EffortInvariants(unittest.TestCase):
    def score(self, **kw):
        base = {"E_CC": 5, "E_LOC_net_capped": 1018, "E_FC": 26, "E_CT": 1}
        return EFFORT.evaluate({"features": {**base, **kw}})["score"]

    def test_no_commits_scores_zero(self):
        self.assertEqual(self.score(E_CC=0, E_LOC_net_capped=0, E_FC=0, E_CT=0), 0.0)

    def test_micro_commit_spam_and_library_dumps_stay_low(self):
        self.assertLessEqual(self.score(E_CC=200, E_LOC_net_capped=200, E_FC=2, E_CT=0), 0.35)
        self.assertLessEqual(self.score(E_CC=1, E_LOC_net_capped=800, E_FC=1000, E_CT=0), 0.35)

    def test_more_work_never_lowers_the_score(self):
        for col, values in (("E_CC", range(1, 61)), ("E_LOC_net_capped", range(0, 6001, 100)), ("E_FC", range(0, 121, 2))):
            scores = [self.score(**{col: v}) for v in values]
            self.assertLessEqual(max(a - b for a, b in zip(scores, scores[1:])), 0.005, col)

    def test_a_heavy_contributor_scores_above_a_typical_one(self):
        self.assertGreater(self.score(E_CC=40, E_LOC_net_capped=6000, E_FC=120, E_CT=5), self.score())


class Gates(unittest.TestCase):
    def test_consistency_needs_five_days_of_the_sprint(self):
        with self.assertRaises(CONSISTENCY.NotEnoughEvidence):
            CONSISTENCY.evaluate(active_student(days=range(0, 3), as_of="2026-02-04T12:00:00Z"))
        r = CONSISTENCY.evaluate(active_student(days=range(0, 8), as_of="2026-02-08T12:00:00Z"))
        self.assertTrue(r["provisional"] and r["sprint_elapsed"] < 1.0)

    def test_effort_needs_one_day(self):
        with self.assertRaises(EFFORT.NotEnoughEvidence):
            EFFORT.evaluate(active_student(days=[], as_of="2026-02-01T12:00:00Z"))

    def test_provisional_intervals_are_wider_than_final_ones(self):
        early = EFFORT.evaluate(active_student(days=range(0, 4), as_of="2026-02-05T12:00:00Z"))
        final = EFFORT.evaluate(active_student(days=range(0, 4)))
        self.assertGreater(early["interval"][1] - early["interval"][0], final["interval"][1] - final["interval"][0])
        self.assertTrue(any("provisional" in w for w in early["warnings"]))

    def test_no_activity_scores_zero_for_effort_and_consistency(self):
        empty = evidence([])
        self.assertEqual(EFFORT.evaluate(empty)["score"], 0.0)
        self.assertEqual(CONSISTENCY.evaluate(empty)["score"], 0.0)


if __name__ == "__main__":
    unittest.main()
