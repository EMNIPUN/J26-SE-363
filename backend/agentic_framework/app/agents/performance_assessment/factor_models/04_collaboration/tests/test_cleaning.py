"""Run from factor_models/:  python -m unittest discover -s 04_collaboration/tests"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE.parents[1]))

from cleaning import clean_text, featurize, substance  # noqa: E402
from evidence.testing import evidence  # noqa: E402

REAL = "The seat check and the insert are separate steps, so two requests at the same moment can both pass the check and overbook the event. Use a transaction."


class CollaborationCleaning(unittest.TestCase):
    def test_approvals_score_zero(self):
        for text in ("LGTM", "ok", "looks good", "👍", "Thanks!"):
            self.assertEqual(substance(text), 0.0, text)

    def test_quoting_code_and_links_do_not_add_substance(self):
        padded = "> " + REAL + "\n```js\n" + "x = 1\n" * 50 + "```\nhttps://example.com/a/very/long/link/here ok"
        self.assertEqual(substance(padded), 0.0)

    def test_real_review_scores_high(self):
        self.assertGreater(substance(REAL), 0.6)

    def test_repeated_word_padding_scores_zero(self):
        self.assertEqual(substance("fix fix fix fix fix fix fix fix fix fix"), 0.0)

    def test_clean_text(self):
        self.assertEqual(clean_text("@alice please `x()` see https://a.b **now** 😀"), "please see now")

    def test_only_other_peoples_prs_and_no_bots(self):
        ev = evidence([], reviews=[
            {"pr_id": "p1", "reviewer": "STU-001", "pr_author": "STU-002", "state": "COMMENTED", "body": REAL},
            {"pr_id": "p2", "reviewer": "STU-001", "pr_author": "STU-001", "state": "COMMENTED", "body": REAL},
            {"pr_id": "p3", "reviewer": "copilot[bot]", "pr_author": "STU-002", "state": "COMMENTED", "body": REAL}],
            comments=[{"pr_id": "p1", "author": "STU-001", "pr_author": "STU-001", "kind": "discussion", "body": REAL, "is_reply": True, "mentions": 1},
                      {"pr_id": "p1", "author": "STU-001", "pr_author": "STU-002", "kind": "discussion", "body": "Agreed, will do", "is_reply": True, "mentions": 1}],
            pull_requests=[{"id": "p9", "author": "STU-001", "merged_at": "x"}, {"id": "p8", "author": "STU-001", "merged_at": None, "closed_at": None}])
        f = featurize(ev)["features"]
        self.assertEqual((f["Co_CCount"], f["Co_MC"], f["Co_PCount"], f["Co_IR"]), (2, 2, 1, 0.5))
        self.assertGreater(f["Co_PRC_depth"], 0.6)

    def test_no_pull_requests_warns(self):
        self.assertTrue(featurize(evidence([]))["warnings"])


if __name__ == "__main__":
    unittest.main()
