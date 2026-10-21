"""Run from factor_models/:  python -m unittest discover -s 04_collaboration/tests

The invariants of PROTOCOL.md for the fixed-weight Collaboration score, the evidence gate, and the entry point used by the agent's bridge.
"""
import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))

from evidence.testing import evidence  # noqa: E402


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE.parents[1] / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = load("t_collab_score", "score.py")
E = load("t_collab_evaluate", "evaluate.py")

REAL = ("The seat check and the insert are separate steps, so two requests at the same moment can both pass the check and overbook the event. "
        "Use a transaction around both.")
REAL2 = "This query runs once per row, so the page will slow down with many events. Fetch them in one query with a join instead."


def review(i, body, reviewer="STU-001", author="STU-002"):
    return {"pr_id": f"p{i}", "reviewer": reviewer, "pr_author": author, "state": "COMMENTED", "body": body}


def ev(reviews=(), comments=(), prs=(), team=None, merged=0):
    extra = {"reviews": list(reviews), "comments": list(comments), "pull_requests": list(prs), "merged_for_others": merged}
    if team is not None:
        extra["team"] = {"reviews_and_comments": team}
    return evidence([], **extra)


class Gate(unittest.TestCase):
    def test_a_team_with_no_review_activity_gives_no_score_not_zero(self):
        r = S.assess(ev(team=0))
        self.assertIsNone(r["score"])
        self.assertTrue(any("not available" in w for w in r["warnings"]))

    def test_a_student_who_does_nothing_in_a_reviewing_team_scores_zero(self):
        r = S.assess(ev(team=7))
        self.assertEqual(r["score"], 0.0)

    def test_unknown_team_and_no_activity_is_not_available(self):
        self.assertIsNone(S.assess(ev())["score"])

    def test_unknown_team_with_activity_scores_and_says_so(self):
        r = S.assess(ev(reviews=[review(1, REAL)]))
        self.assertIsNotNone(r["score"])
        self.assertTrue(any("not supplied" in w for w in r["warnings"]))


class Invariants(unittest.TestCase):
    def test_approvals_and_one_word_texts_do_not_raise_the_score(self):
        base = S.assess(ev(reviews=[review(1, REAL)], team=3))["score"]
        spam = [review(i, t) for i, t in enumerate(["LGTM", "ok", "looks good", "👍", "Thanks!", "+1", "done"] * 6, start=10)]
        padded = S.assess(ev(reviews=[review(1, REAL)] + spam, team=3))["score"]
        self.assertLessEqual(padded, base + 1e-9)

    def test_quoted_pasted_and_repeated_padding_does_not_help(self):
        pad = [review(2, "> " + REAL + "\n```js\n" + "x = 1\n" * 40 + "```\nhttps://example.com/long/link ok"), review(3, "fix fix fix fix fix fix fix fix fix fix")]
        a = S.assess(ev(reviews=[review(1, REAL)], team=3))["score"]
        b = S.assess(ev(reviews=[review(1, REAL)] + pad, team=3))["score"]
        self.assertLessEqual(b, a + 1e-9)

    def test_more_substantive_reviews_never_lower_the_score(self):
        scores = []
        for n in range(0, 5):
            texts = [REAL, REAL2, REAL + " Also add a test.", REAL2 + " Measure it first."][:n]
            scores.append(S.assess(ev(reviews=[review(i, t) for i, t in enumerate(texts)], team=3))["score"])
        self.assertEqual(scores, sorted(scores))

    def test_self_comments_and_bots_do_not_count(self):
        a = S.assess(ev(team=3))["score"]
        b = S.assess(ev(reviews=[review(1, REAL, author="STU-001"), review(2, REAL, reviewer="copilot[bot]")], team=3))["score"]
        self.assertEqual(a, b)

    def test_scores_stay_in_range_and_are_deterministic(self):
        e = ev(reviews=[review(i, REAL) for i in range(8)], comments=[{"pr_id": "p1", "author": "STU-001", "pr_author": "STU-002", "kind": "discussion", "body": REAL2,
                                                                       "is_reply": True, "mentions": 2}] * 6, prs=[{"id": "x", "author": "STU-001", "merged_at": "t"}], merged=4, team=9)
        r1, r2 = S.assess(e), S.assess(e)
        self.assertEqual(r1, r2)
        self.assertTrue(0.0 <= r1["score"] <= 1.0)
        lo, hi = r1["interval"]
        self.assertTrue(0.0 <= lo <= r1["score"] + 0.35 and hi <= 1.0)

    def test_a_measure_without_evidence_is_left_out_not_counted_as_zero(self):
        m, _ = S.measures(ev(reviews=[review(1, REAL)], team=3))
        self.assertIsNone(m["response_rate"])          # no own pull request
        self.assertIsNone(m["issue_substance"])         # no discussion comment
        with_ir = dict(m, response_rate=0.0)
        self.assertGreater(S.combine(m), S.combine(with_ir))

    def test_weights_renormalise_over_the_measures_that_exist(self):
        self.assertAlmostEqual(S.combine({"review_substance": 0.8, "response_rate": None, "issue_substance": None, "mentions_replies": 0.0, "reviewed_prs": 0.0, "authored_comments": 0.0}),
                               0.8 / 4)


class EntryPoint(unittest.TestCase):
    def test_evaluate_returns_the_standard_result(self):
        r = E.evaluate(ev(reviews=[review(1, REAL)], team=3))
        for key in ("factor", "score", "interval", "features", "removed", "versions", "warnings"):
            self.assertIn(key, r)
        self.assertEqual(r["versions"]["score"], S.SCORE_VERSION)

    def test_a_gated_score_raises_so_the_bridge_falls_back_and_fusion_redistributes(self):
        with self.assertRaises(E.NotEnoughEvidence):
            E.evaluate(ev(team=0))

    def test_a_feature_payload_goes_to_the_existing_simulator(self):
        out = asyncio.run(E.async_evaluate({"features": {"Co_PCount": 3, "Co_CCount": 5}}, {"simulation_mode": "quick"}))
        self.assertIn("score", out)

    def test_evidence_in_a_payload_is_found(self):
        r = asyncio.run(E.async_evaluate({"evidence": ev(reviews=[review(1, REAL)], team=3)}))
        self.assertEqual(r["factor"], "collaboration")


if __name__ == "__main__":
    unittest.main()
