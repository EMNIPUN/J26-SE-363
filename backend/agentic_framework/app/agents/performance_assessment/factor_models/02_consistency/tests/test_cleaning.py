"""Run from factor_models/:  python -m unittest discover -s 02_consistency/tests"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE.parents[1]))

from cleaning import featurize  # noqa: E402
from evidence.testing import commit, evidence, file  # noqa: E402


def day(n, hour=10):
    return f"2026-02-{2 + n:02d}T{hour:02d}:00:00+05:30"


class ConsistencyCleaning(unittest.TestCase):
    def test_readme_commits_do_not_make_days_active(self):
        real = [commit(f"r{i}", day(i), [file("src/a.js", code=20)]) for i in (0, 6, 12)]
        fake = [commit(f"d{i}", day(i), [file("README.md", code=5)]) for i in (1, 2, 3, 4, 5, 7, 8, 9, 10, 11)]
        f = featurize(evidence(real + fake))["features"]
        self.assertAlmostEqual(f["C_AWR"], 3 / 14, places=3)

    def test_comment_padding_does_not_change_rhythm(self):
        plain = evidence([commit("a", day(0), [file("src/a.js", code=50)]), commit("b", day(13), [file("src/a.js", code=50)])])
        padded = evidence([commit("a", day(0), [file("src/a.js", code=50)]), commit("b", day(13), [file("src/a.js", code=50, comment=900, blank=400)])])
        self.assertEqual(featurize(plain)["features"], featurize(padded)["features"])

    def test_last_minute_work_is_flagged(self):
        late = evidence([commit("a", day(12), [file("src/a.js", code=80)]), commit("b", day(13), [file("src/a.js", code=120)])])
        f = featurize(late)["features"]
        self.assertEqual(f["C_DC"], 1.0)
        self.assertEqual(f["C_first_active_day"], 12)

    def test_two_bursts(self):
        ev = evidence([commit("a", day(0), [file("src/a.js", code=100)]), commit("b", day(1), [file("src/a.js", code=80)]),
                       commit("c", day(11), [file("src/a.js", code=100)]), commit("d", day(12), [file("src/a.js", code=90)])])
        self.assertEqual(featurize(ev)["features"]["C_bimodal"], 1)

    def test_no_work(self):
        out = featurize(evidence([commit("a", day(2), [file("README.md", code=10)])]))
        self.assertEqual(out["features"]["C_no_activity"], 1)
        self.assertTrue(out["warnings"])

    def test_commits_outside_the_window_are_ignored(self):
        ev = evidence([commit("a", "2026-03-30T10:00:00+05:30", [file("src/a.js", code=10)])])
        self.assertEqual(featurize(ev)["features"]["C_no_activity"], 1)


if __name__ == "__main__":
    unittest.main()
