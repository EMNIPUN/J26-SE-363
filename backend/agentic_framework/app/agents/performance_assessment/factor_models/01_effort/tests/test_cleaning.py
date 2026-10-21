"""Run from factor_models/:  python -m unittest discover -s 01_effort/tests"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE.parents[1]))

from cleaning import featurize  # noqa: E402
from evidence.testing import commit, evidence, file  # noqa: E402


class EffortCleaning(unittest.TestCase):
    def test_padding_does_not_raise_effort(self):
        honest = evidence([commit("a", "2026-02-03T10:00:00+05:30", [file("src/a.js", code=40)])])
        padded = evidence([commit("a", "2026-02-03T10:00:00+05:30", [
            file("src/a.js", code=40, comment=300, blank=200), file("README.md", code=500), file("package.json", code=80)])])
        f1, f2 = featurize(honest)["features"], featurize(padded)["features"]
        self.assertEqual(f1["E_LOC_added"], f2["E_LOC_added"])
        self.assertEqual(f1["E_FC"], f2["E_FC"])

    def test_docs_only_and_reformat_commits_are_not_effort(self):
        ev = evidence([
            commit("docs", "2026-02-03T10:00:00+05:30", [file("README.md", code=200)]),
            commit("fmt", "2026-02-04T10:00:00+05:30", [file("src/a.js", format_only=300, d_format=300)]),
            commit("real", "2026-02-05T10:00:00+05:30", [file("src/a.js", code=25, d_code=5)])])
        out = featurize(ev)
        self.assertEqual(out["features"]["E_CC"], 1)
        self.assertEqual(out["features"]["E_LOC_net"], 20)
        self.assertEqual(out["commits_not_counted"], 2)

    def test_merges_and_bulk_uploads_are_excluded(self):
        bulk = commit("bulk", "2026-02-03T10:00:00+05:30", [file(f"lib/f{i}.js", code=10) for i in range(151)])
        merge = commit("m", "2026-02-03T11:00:00+05:30", [file("src/a.js", code=50)], is_merge=True)
        ok = commit("ok", "2026-02-03T12:00:00+05:30", [file("src/a.js", code=10)])
        self.assertEqual(featurize(evidence([bulk, merge, ok]))["features"]["E_CC"], 1)

    def test_commit_cap(self):
        ev = evidence([commit("big", "2026-02-03T10:00:00+05:30", [file("src/a.js", code=5000)])])
        f = featurize(ev)["features"]
        self.assertEqual((f["E_LOC_net"], f["E_LOC_net_capped"]), (5000, 800))

    def test_tasks_and_reviews(self):
        ev = evidence([commit("a", "2026-02-03T10:00:00+05:30", [file("src/a.js", code=5)])], merged_for_others=2,
                      tasks=[{"assignee": "STU-001", "status": "Done", "completed_by": "STU-001"},
                             {"assignee": "STU-001", "status": "Done", "completed_by": "STU-009"},
                             {"assignee": "STU-001", "status": "To Do", "completed_by": None}],
                      reviews=[{"reviewer": "STU-001", "pr_author": "STU-002"}, {"reviewer": "STU-001", "pr_author": "STU-001"}],
                      comments=[{"author": "STU-001", "pr_author": "STU-003"}])
        f = featurize(ev)["features"]
        self.assertEqual((f["E_CT"], f["E_RD"]), (1, 4))

    def test_invalid_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            featurize({"schema": "evidence/1"})


if __name__ == "__main__":
    unittest.main()
