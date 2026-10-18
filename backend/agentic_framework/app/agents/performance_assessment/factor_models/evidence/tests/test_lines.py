"""Run:  python -m unittest discover -s evidence/tests   (from factor_models/)"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evidence.lines import (  # noqa: E402
    classify_path, clean_counts, clean_patch, removed_summary, stats_from_patch, strip_comments_and_blanks)


def patch(*lines):
    return "@@ -1,1 +1,1 @@\n" + "\n".join(lines)


class PathKinds(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(classify_path("src/App.jsx"), "code")
        self.assertEqual(classify_path("src/App.test.jsx"), "test")
        self.assertEqual(classify_path("tests/test_loans.py"), "test")
        self.assertEqual(classify_path("README.md"), "docs")
        self.assertEqual(classify_path("docs/guide.md"), "docs")
        self.assertEqual(classify_path("pom.xml"), "config")
        self.assertEqual(classify_path("package-lock.json"), "generated")
        self.assertEqual(classify_path("node_modules/x/index.js"), "generated")
        self.assertEqual(classify_path("logo.png"), "asset")
        self.assertEqual(classify_path("data/users.csv"), "data")
        self.assertEqual(classify_path("src/main/java/a/B.java"), "code")
        self.assertEqual(classify_path("src/test/java/a/BTest.java"), "test")


class Counting(unittest.TestCase):
    def test_comment_spam_does_not_count(self):
        p = patch("+// TODO", "+// another comment", "+/* block", "+ * more", "+ */", "+const x = 1;", "+")
        s = stats_from_patch("a.js", p)["added"]
        self.assertEqual((s["code"], s["comment"], s["blank"]), (1, 5, 1))

    def test_python_hash_and_docstring(self):
        p = patch('+"""Docstring', "+more text", '+"""', "+# note", "+def f():", "+    return 1")
        s = stats_from_patch("a.py", p)["added"]
        self.assertEqual((s["code"], s["comment"]), (2, 4))

    def test_one_line_docstring_and_trailing_comment(self):
        p = patch('+"""One liner."""', "+x = 1  # keep")
        s = stats_from_patch("a.py", p)["added"]
        self.assertEqual((s["code"], s["comment"]), (1, 1))

    def test_html_comment(self):
        p = patch("+<!-- header -->", "+<div>hi</div>")
        s = stats_from_patch("a.html", p)["added"]
        self.assertEqual((s["code"], s["comment"]), (1, 1))

    def test_commented_out_code_is_a_comment(self):
        p = patch("+// const old = compute(a, b);", "+const fresh = compute(a);")
        s = stats_from_patch("a.js", p)["added"]
        self.assertEqual((s["code"], s["comment"]), (1, 1))

    def test_jsdoc_continuation_without_the_opening(self):
        p = patch("+ * @param x the input", "+ */", "+function f(x) {", "+}")
        s = stats_from_patch("a.js", p)["added"]
        self.assertEqual((s["code"], s["comment"]), (2, 2))

    def test_reformat_all_is_not_new_work(self):
        p = patch("-function  total(a,b){ return a+b; }", "-const   result=total(1,2);",
                  "+function total(a, b) { return a + b; }", "+const result = total(1, 2);")
        s = stats_from_patch("a.js", p)
        self.assertEqual((s["added"]["code"], s["added"]["format_only"]), (0, 2))
        self.assertEqual((s["deleted"]["code"], s["deleted"]["format_only"]), (0, 2))

    def test_moved_lines_in_one_file_are_not_new_work(self):
        p = patch("-  const taxRate = loadRate(region);", "+  const taxRate = loadRate(region);")
        s = stats_from_patch("a.js", p)
        self.assertEqual(s["added"]["code"], 0)

    def test_short_lines_are_not_format_only(self):
        p = patch("-}", "+}", "+const added = 1;")
        s = stats_from_patch("a.js", p)
        self.assertEqual(s["added"]["code"], 2)

    def test_genuine_change_survives(self):
        p = patch("-const rate = 0.08;", "+const rate = 0.10;")
        s = stats_from_patch("a.js", p)
        self.assertEqual((s["added"]["code"], s["deleted"]["code"]), (1, 1))


class CleanCounts(unittest.TestCase):
    def test_docs_and_config_never_count(self):
        s = stats_from_patch("README.md", patch("+# Title", "+text " * 3, "+more"))
        self.assertEqual(clean_counts("docs", s), (0, 0))
        self.assertEqual(clean_counts("config", s), (0, 0))
        self.assertEqual(clean_counts("generated", s), (0, 0))

    def test_tests_count_as_source(self):
        s = stats_from_patch("a.test.js", patch("+expect(a).toBe(1);", "+// note"))
        self.assertEqual(clean_counts("test", s), (1, 0))

    def test_removed_summary(self):
        a = stats_from_patch("a.js", patch("+// c", "+", "+x();"))
        b = stats_from_patch("README.md", patch("+one", "+two"))
        c = stats_from_patch("lock.json", patch("+x"))
        out = removed_summary([("code", a), ("docs", b), ("generated", c)])
        self.assertEqual(out, {"comment": 1, "blank": 1, "format_only": 0, "docs_or_config": 2, "generated_or_data": 1})


class Text(unittest.TestCase):
    def test_strip_comments_and_blanks(self):
        text = "// header\nconst a = 1;\n\n/* x\n y */\nconst b = 2;"
        self.assertEqual(strip_comments_and_blanks("a.js", text), "const a = 1;\nconst b = 2;")

    def test_clean_patch_drops_comment_and_moved_lines(self):
        p = ("@@ -1,3 +1,3 @@\n+// explain\n-const keep =  1;\n+const keep = 1;\n+const newOne = fetchAll();")
        out = clean_patch("a.js", p)
        self.assertIn("newOne", out)
        self.assertNotIn("explain", out)
        self.assertNotIn("keep", out)


if __name__ == "__main__":
    unittest.main()
