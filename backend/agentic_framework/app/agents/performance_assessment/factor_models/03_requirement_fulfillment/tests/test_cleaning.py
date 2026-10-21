"""Run from factor_models/:  python -m unittest discover -s 03_requirement_fulfillment/tests"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE.parents[1]))

from cleaning import clean_task_diff, featurize  # noqa: E402
from evidence.testing import commit, evidence, file  # noqa: E402

PATCH = ("@@ -1,2 +1,6 @@\n+// handles empty carts and every edge case perfectly\n+function total(cart) {\n+  return cart.reduce((s, l) => s + l.price * l.qty, 0);\n"
         "+}\n+\n+/* TODO: tax */")


class RequirementFulfilment(unittest.TestCase):
    def test_comments_never_reach_the_judge(self):
        f = file("src/cart.js", code=3)
        f["patch"] = PATCH
        c = commit("c1", "2026-02-03T10:00:00+05:30", [f, {"path": "README.md", "added": 9, "deleted": 0, "patch": "@@ -0,0 +1 @@\n+hello"}])
        out = clean_task_diff(evidence([c]), {"commit_ids": ["c1"]})
        self.assertIn("function total", out["diff"])
        self.assertNotIn("handles empty carts", out["diff"])
        self.assertNotIn("TODO", out["diff"])
        self.assertNotIn("README", out["diff"])
        self.assertEqual(out["files"], ["src/cart.js"])

    def test_long_diff_is_cut_with_a_marker(self):
        f = file("src/a.js", code=1)
        f["patch"] = "@@ -0,0 +1 @@\n+" + "x = 1; " * 500
        out = clean_task_diff(evidence([commit("c1", "2026-02-03T10:00:00+05:30", [f])]), {"commit_ids": ["c1"]}, limit=100)
        self.assertTrue(out["truncated"])
        self.assertIn("[diff cut here]", out["diff"])

    def test_board_features(self):
        ev = evidence([commit("c1", "2026-02-03T10:00:00+05:30", [file("src/a.js", code=5)]), commit("c2", "2026-02-04T10:00:00+05:30", [file("src/b.js", code=5)])],
                      tasks=[{"assignee": "STU-001", "status": "Done", "completed_by": "STU-001", "acceptance_criteria": ["a", "b"], "criteria_met": 2, "llm_rating": 4, "commit_ids": ["c1"]},
                             {"assignee": "STU-001", "status": "Done", "completed_by": "STU-002", "acceptance_criteria": ["a"], "criteria_met": 1, "llm_rating": 2, "commit_ids": []},
                             {"assignee": "STU-001", "status": "To Do", "acceptance_criteria": ["a"], "criteria_met": 0, "llm_rating": 1, "commit_ids": []}])
        f = featurize(ev)["features"]
        self.assertEqual((f["RF_tasks_assigned"], f["RF_tasks_done"], f["RF_done_by_teammate"], f["RF_tasks_not_started"]), (3, 1, 1, 1))
        self.assertEqual(f["RF_ac_met"], 2)  # the teammate's work is not credited
        self.assertAlmostEqual(f["RF_ac_ratio"], 0.5)
        self.assertAlmostEqual(f["RF_untracked_ratio"], 0.5)


if __name__ == "__main__":
    unittest.main()
