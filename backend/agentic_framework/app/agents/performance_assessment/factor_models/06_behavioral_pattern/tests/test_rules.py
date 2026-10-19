"""Run from factor_models/:  python -m unittest discover -s 06_behavioral_pattern/tests

The invariants of training/PROTOCOL.md for the Behavioral Pattern rules: each rule fires on its condition only, modifiers stay in their ranges, missing inputs never create a penalty
or a reward, overlap is resolved by one stated rule, and everything is deterministic.
"""
import importlib.util
import itertools
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE.parents[1] / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = load("t_bp_rules", "rules.py")
E = load("t_bp_evaluate", "evaluate.py")
TH = R.PROPOSAL
GRID = [i / 20 for i in range(21)]


def cls(e, c, co=None, bimodal=0):
    return R.classify({"E": e, "C": c, "Co": co}, bimodal, TH)


class EachRule(unittest.TestCase):
    def test_consistent_deep_contributor(self):
        self.assertEqual(cls(0.8, 0.8, 0.5)["persona"], "Consistent deep contributor")

    def test_last_minute_rusher(self):
        self.assertEqual(cls(0.8, 0.2, 0.5)["persona"], "Last-minute rusher")

    def test_reviewer_or_coordinator(self):
        self.assertEqual(cls(0.2, 0.5, 0.8)["persona"], "Reviewer or coordinator")

    def test_burst_worker(self):
        self.assertEqual(cls(0.8, 0.5, 0.5, bimodal=1)["persona"], "Burst worker")

    def test_free_rider(self):
        self.assertEqual(cls(0.1, 0.5, 0.1)["persona"], "Free rider")

    def test_no_rule_is_balanced_contributor_with_a_neutral_modifier(self):
        r = cls(0.5, 0.5, 0.5)
        self.assertEqual((r["persona"], r["score_modifier"]), ("Balanced contributor", 1.0))

    def test_conditions_are_strict_inequalities(self):
        self.assertEqual(cls(0.7, 0.8, 0.5)["persona"], "Balanced contributor")
        self.assertEqual(cls(0.3, 0.5, 0.3)["persona"], "Balanced contributor")


class Modifier(unittest.TestCase):
    def test_always_inside_the_patterns_range_and_the_cap(self):
        for e, c, co, b in itertools.product(GRID, GRID, GRID + [None], (0, 1)):
            r = cls(e, c, co, b)
            self.assertTrue(R.MODIFIER_CAP[0] <= r["score_modifier"] <= R.MODIFIER_CAP[1])
            if r["persona"] in R.RANGES:
                lo, hi = sorted(R.RANGES[r["persona"]])
                self.assertTrue(lo - 1e-9 <= r["score_modifier"] <= hi + 1e-9, (e, c, co, b, r["persona"], r["score_modifier"]))

    def test_stronger_evidence_moves_the_modifier_toward_the_strong_end(self):
        weak, strong = cls(0.72, 0.72)["score_modifier"], cls(0.98, 0.98)["score_modifier"]
        self.assertTrue(1.10 <= weak < strong <= 1.20)
        rweak, rstrong = cls(0.1, 0.5, 0.28)["score_modifier"], cls(0.0, 0.5, 0.0)["score_modifier"]
        self.assertTrue(0.80 <= rstrong < rweak <= 0.85)

    def test_near_a_threshold_is_flagged(self):
        self.assertTrue(cls(0.71, 0.9)["near_threshold"])
        self.assertFalse(cls(0.95, 0.95)["near_threshold"])


class Overlap(unittest.TestCase):
    def test_rusher_and_burst_together_gives_the_milder_modifier(self):
        r = cls(0.8, 0.2, 0.5, bimodal=1)
        self.assertEqual(r["persona"], "Burst worker")
        self.assertEqual(sorted(r["matched"]), ["Burst worker", "Last-minute rusher"])
        self.assertTrue(any("milder" in w for w in r["warnings"]))

    def test_no_other_pair_of_rules_can_match_together(self):
        allowed = {frozenset(("Last-minute rusher", "Burst worker")), frozenset(("Consistent deep contributor", "Burst worker"))}
        for e, c, co, b in itertools.product(GRID, GRID, GRID + [None], (0, 1)):
            m = cls(e, c, co, b)["matched"]
            if len(m) > 1:
                self.assertIn(frozenset(m), allowed, (e, c, co, b, m))

    def test_consistent_and_burst_together_gives_the_milder_modifier(self):
        r = cls(0.8, 0.8, 0.5, bimodal=1)
        self.assertEqual(abs(r["score_modifier"] - 1.0) <= abs(R.modifier_for("Consistent deep contributor", r["strength"]) - 1.0), True)


class MissingInputs(unittest.TestCase):
    def test_collaboration_missing_never_gives_reviewer_or_free_rider(self):
        for e, c, b in itertools.product(GRID, GRID, (0, 1)):
            self.assertNotIn(cls(e, c, None, b)["persona"], ("Reviewer or coordinator", "Free rider"))

    def test_collaboration_missing_still_allows_the_other_three_rules_and_says_what_was_skipped(self):
        r = cls(0.8, 0.8, None)
        self.assertEqual(r["persona"], "Consistent deep contributor")
        self.assertEqual(set(r["untestable_rules"]), {"Reviewer or coordinator", "Free rider"})
        self.assertTrue(any("Collaboration not available" in w for w in r["warnings"]))

    def test_low_effort_with_no_collaboration_score_is_not_a_free_rider(self):
        r = cls(0.05, 0.5, None)
        self.assertEqual((r["persona"], r["score_modifier"]), ("Balanced contributor", 1.0))

    def test_effort_or_consistency_missing_is_unclassified_and_neutral(self):
        for e, c in ((None, 0.5), (0.5, None), (None, None), (1.4, 0.5), (0.5, -0.1)):
            r = cls(e, c, 0.5)
            self.assertEqual((r["persona"], r["score_modifier"]), ("Unclassified", 1.0))

    def test_bimodal_flag_missing_only_disables_the_burst_rule(self):
        r = R.classify({"E": 0.8, "C": 0.5, "Co": 0.5}, None, TH)
        self.assertEqual(r["persona"], "Balanced contributor")
        self.assertIn("Burst worker", r["untestable_rules"])


class Thresholds(unittest.TestCase):
    def test_lower_cut_points_make_the_same_scores_fire(self):
        low = dict(R.PROPOSAL, name="low", E_high=0.5, C_high=0.5)
        self.assertEqual(R.classify({"E": 0.55, "C": 0.55, "Co": 0.2}, 0, low)["persona"], "Consistent deep contributor")
        self.assertEqual(R.classify({"E": 0.55, "C": 0.55, "Co": 0.2}, 0, TH)["persona"], "Balanced contributor")

    def test_default_thresholds_load_and_are_named(self):
        self.assertIn(R.load_thresholds()["name"], ("proposal", "calibrated"))


class Extensions(unittest.TestCase):
    """Rules version 2: late-churn path for Last-minute rusher, effort-only Free rider (training/PROTOCOL.md amendments A and B)."""
    X = dict(R.PROPOSAL, name="ext", ext_rusher=True, ext_free_rider=True, E_med=0.4, DC_high=0.5, E_low=0.2, C_low=0.1)

    def go(self, e, c, co=None, bimodal=0, late=None, th=None):
        return R.classify({"E": e, "C": c, "Co": co}, bimodal, th or self.X, late)

    def test_high_late_churn_makes_a_last_minute_rusher_even_when_consistency_is_not_tiny(self):
        r = self.go(0.6, 0.35, 0.5, late=0.8)
        self.assertEqual(r["persona"], "Last-minute rusher")
        self.assertTrue(0.90 <= r["score_modifier"] <= 0.95)

    def test_without_the_extension_the_same_student_is_balanced(self):
        r = self.go(0.6, 0.35, 0.5, late=0.8, th=dict(self.X, ext_rusher=False))
        self.assertEqual(r["persona"], "Balanced contributor")

    def test_the_proposals_own_path_still_works(self):
        self.assertEqual(self.go(0.6, 0.05, 0.5, late=None)["persona"], "Last-minute rusher")

    def test_late_churn_below_the_cut_or_missing_does_not_fire(self):
        self.assertEqual(self.go(0.6, 0.35, 0.5, late=0.2)["persona"], "Balanced contributor")
        r = self.go(0.6, 0.35, 0.5, late=None)
        self.assertEqual(r["persona"], "Balanced contributor")
        self.assertTrue(any("late-churn share not available" in w for w in r["warnings"]))

    def test_low_effort_with_a_late_churn_is_not_a_rusher(self):
        self.assertNotEqual(self.go(0.3, 0.35, 0.5, late=0.9)["persona"], "Last-minute rusher")

    def test_effort_only_free_rider_when_collaboration_is_not_available(self):
        r = self.go(0.02, 0.0, None)
        self.assertEqual((r["persona"], r["evidence"]), ("Free rider", "effort_only"))
        self.assertTrue(0.90 <= r["score_modifier"] <= 0.95)
        self.assertTrue(any("effort alone" in w for w in r["warnings"]))

    def test_with_a_collaboration_score_the_original_free_rider_rule_and_range_apply(self):
        r = self.go(0.02, 0.0, 0.1)
        self.assertEqual((r["persona"], r["evidence"]), ("Free rider", "full"))
        self.assertTrue(0.80 <= r["score_modifier"] <= 0.85)

    def test_effort_only_free_rider_needs_both_low_effort_and_low_consistency(self):
        self.assertEqual(self.go(0.02, 0.6, None)["persona"], "Balanced contributor")
        self.assertEqual(self.go(0.3, 0.0, None)["persona"], "Balanced contributor")

    def test_effort_only_free_rider_is_never_harsher_than_the_milder_range(self):
        for e, c in itertools.product(GRID, GRID):
            r = self.go(e, c, None)
            if r["persona"] == "Free rider":
                self.assertGreaterEqual(r["score_modifier"], 0.90 - 1e-9)

    def test_each_extension_can_be_switched_off_on_its_own(self):
        self.assertEqual(self.go(0.02, 0.0, None, th=dict(self.X, ext_free_rider=False))["persona"], "Balanced contributor")
        self.assertEqual(self.go(0.6, 0.35, 0.5, late=0.8, th=dict(self.X, ext_free_rider=False))["persona"], "Last-minute rusher")

    def test_the_stored_default_set_has_the_adopted_extension_only(self):
        th = R.load_thresholds()
        self.assertTrue(th.get("ext_free_rider"))
        self.assertFalse(th.get("ext_rusher"))

    def test_extensions_are_off_in_the_proposals_own_set(self):
        self.assertEqual(R.classify({"E": 0.02, "C": 0.0, "Co": None}, 0, R.PROPOSAL, None)["persona"], "Balanced contributor")

    def test_modifiers_stay_in_range_with_extensions_on(self):
        for e, c, co, b, late in itertools.product(GRID, GRID, GRID + [None], (0, 1), (None, 0.0, 0.6, 1.0)):
            m = self.go(e, c, co, b, late)["score_modifier"]
            self.assertTrue(R.MODIFIER_CAP[0] <= m <= R.MODIFIER_CAP[1])


class EntryPoint(unittest.TestCase):
    def test_classify_has_the_shape_the_bridge_reads(self):
        out = E.classify({"effort": 0.9, "consistency": 0.9, "collaboration": None, "is_bimodal": 0}, {"bp_thresholds": "proposal"})
        for key in ("persona", "score_modifier", "rationale"):
            self.assertIn(key, out)
        self.assertEqual(out["persona"], "Consistent deep contributor")

    def test_deterministic(self):
        a = cls(0.8, 0.2, 0.4, 1)
        self.assertEqual(a, cls(0.8, 0.2, 0.4, 1))


if __name__ == "__main__":
    unittest.main()
