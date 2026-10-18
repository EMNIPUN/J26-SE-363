"""Run from factor_models/:  python -m unittest discover -s 05_task_complexity/tests"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE.parents[1]))

from cleaning import component, featurize  # noqa: E402
from evidence.testing import commit, evidence, file  # noqa: E402

AT = "2026-02-03T10:00:00+05:30"


def task(tid, commits, sp=3, sc=2):
    return {"id": tid, "assignee": "STU-001", "story_points": sp, "subtask_count": sc, "commit_ids": commits}


class TaskComplexity(unittest.TestCase):
    def test_footprint_ignores_tests_docs_config_and_comment_only_files(self):
        c = commit("c1", AT, [file("src/models/Order.js", code=30), file("src/models/Order.test.js", code=20), file("README.md", code=40),
                              file("package.json", code=3), file("src/utils/notes.js", comment=50), file("src/pages/Cart.jsx", code=15)])
        out = featurize(evidence([c], tasks=[task("t1", ["c1"])], repo={"reach_before": {"src/models/Order.js": 4}}))
        f = out["features"]
        self.assertEqual((f["TC_FI"], f["TC_DR"], f["TC_CB"]), (2, 4, 2))

    def test_new_files_have_no_reach(self):
        c = commit("c1", AT, [file("src/models/New.js", code=30)])
        f = featurize(evidence([c], tasks=[task("t1", ["c1"])], repo={"reach_before": {}}))["features"]
        self.assertEqual(f["TC_DR"], 0)

    def test_task_without_commits_is_missing_not_zero(self):
        f = featurize(evidence([], tasks=[task("t1", [])]))["features"]
        self.assertIsNone(f["TC_FI"])
        self.assertEqual(f["TC_SP"], 3)

    def test_padding_does_not_change_structure(self):
        base = commit("c1", AT, [file("src/a/x.js", code=10)])
        padded = commit("c1", AT, [file("src/a/x.js", code=10, comment=200), file("docs/a.md", code=200), file("src/a/x.test.js", code=90)])
        a = featurize(evidence([base], tasks=[task("t", ["c1"])]))["features"]
        b = featurize(evidence([padded], tasks=[task("t", ["c1"])]))["features"]
        self.assertEqual(a, b)

    def test_explicit_footprint_is_used(self):
        fp = [{"path": "src/a/x.js", "kind": "code", "reach_before": 2}, {"path": "src/b/y.js", "kind": "code", "reach_before": 3},
              {"path": "docs/z.md", "kind": "docs", "reach_before": 9}]
        t = dict(task("t", []), footprint=fp)
        f = featurize(evidence([], tasks=[t]))["features"]
        self.assertEqual((f["TC_FI"], f["TC_DR"], f["TC_CB"]), (2, 5, 2))

    def test_component(self):
        self.assertEqual(component("src/main/java/clinic/service/X.java"), "clinic/service")
        self.assertEqual(component("README.md"), "(root)")


if __name__ == "__main__":
    unittest.main()
