"""Run from factor_models/:  python -m unittest discover -s 07_code_ownership/tests"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE.parents[1]))

from cleaning import featurize, meaningful_blame_counts, snippet_candidates, summarize  # noqa: E402
from evidence.testing import commit, evidence, file  # noqa: E402

A, B = "a" * 40, "b" * 40


def porcelain(*rows):
    out = []
    for i, (sha, text) in enumerate(rows, 1):
        out += [f"{sha} {i} {i} 1", "author x", "summary y", "filename f", "\t" + text]
    return "\n".join(out)


class Ownership(unittest.TestCase):
    def test_blame_ignores_comments_and_blank_lines(self):
        p = porcelain((A, "// header"), (A, "const x = 1;"), (A, ""), (B, "/* block"), (B, " * more"), (B, " */"), (B, "run(x);"))
        self.assertEqual(meaningful_blame_counts(p, "src/a.js"), {A: 1, B: 1})

    def test_docs_and_generated_files_are_not_blamed(self):
        p = porcelain((A, "# title"), (A, "text"))
        self.assertEqual(meaningful_blame_counts(p, "README.md"), {})
        self.assertEqual(meaningful_blame_counts(p, "dist/bundle.js"), {})

    def test_summary(self):
        files = {"a.js": {A: 30, B: 5}, "b.js": {A: 4, B: 40}, "c.js": {B: 9}, "d.js": {}}
        s = summarize(files, [A], added_lines=60)
        self.assertEqual(s, {"added_lines": 60, "surviving_lines": 34, "files": 3, "primary_files": 1, "owned_files": 1})

    def test_features(self):
        ev = evidence([], ownership={"added_lines": 60, "surviving_lines": 34, "files": 3, "primary_files": 1, "owned_files": 1})
        f = featurize(ev)
        self.assertAlmostEqual(f["features"]["KO_survival"], 0.5667, places=3)
        self.assertAlmostEqual(f["features"]["KO_primary_owner_share"], 0.3333, places=3)
        self.assertTrue(any("quiz" in w for w in f["warnings"]))

    def test_survival_never_above_one(self):
        ev = evidence([], ownership={"added_lines": 10, "surviving_lines": 25, "files": 1, "primary_files": 1, "owned_files": 1})
        self.assertEqual(featurize(ev)["features"]["KO_survival"], 1.0)

    def test_snippets_skip_getters_and_short_functions(self):
        text = ("def get_name(self):\n    return self.name\n\n"
                "def compute(a, b):\n    # sum things\n    t = 0\n    for x in a:\n        t += x\n    for y in b:\n        t += y\n"
                "    if t > 10:\n        t -= 1\n    return t\n\n"
                "def tiny():\n    return 1\n")
        names = [s["name"] for s in snippet_candidates("app/x.py", text)]
        self.assertEqual(names, ["compute"])

    def test_snippets_in_braces_language(self):
        body = "\n".join(f"    int v{i} = {i};" for i in range(9))
        text = f"public class A {{\n  public int getX() {{\n    return 1;\n  }}\n  public int run() {{\n{body}\n    return v0;\n  }}\n}}\n"
        self.assertIn("run", [s["name"] for s in snippet_candidates("src/A.java", text)])


if __name__ == "__main__":
    unittest.main()
