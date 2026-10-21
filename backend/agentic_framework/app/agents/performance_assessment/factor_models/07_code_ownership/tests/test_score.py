"""Run from factor_models/:  python -m unittest discover -s 07_code_ownership/tests

Answer scoring (phase 2): guards, hand-built features, the entry point's gating rules, and (when numpy and scikit-learn are installed) the whole path with a fake encoder.
"""
import asyncio
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE.parents[1] / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


KF = load("t_ko_features", "ko_features.py")
E = load("t_ko_evaluate", "evaluate.py")
S = E._score  # the very module instance the entry point uses, so patches to its model folder apply to both
QS = load("t_ko_questions2", "questions.py")

CODE = """def cart_total(items, discount):
    if discount < 0:
        raise ValueError("discount must not be negative")
    total = 0
    for item in items:
        if item["qty"] <= 0:
            continue
        total += item["price"] * item["qty"]
    total = total - total * discount
    return round(total, 2)"""
QUESTION = "In cart_total, what happens when `discount < 0` is true, and why is that case rejected?"
FACTS = {"name": "cart_total", "params": ["items", "discount"], "guards": [{"cond": "discount < 0", "raises": "ValueError"}], "handlers": [], "early_returns": [], "loops": [{"target": "item", "iter": "items"}],
         "calls": [], "returns": ["round(total, 2)"], "recursive": False}
GOOD = "It raises a ValueError saying the discount must not be negative. A negative discount would raise the total instead of lowering it, so the function refuses it before it does any of the summing."
VAGUE = "It handles the input and returns the correct result in the end."


class Guards(unittest.TestCase):
    def test_empty_and_very_short_answers_are_guarded(self):
        self.assertIsNotNone(KF.guard("", QUESTION, CODE))
        self.assertIsNotNone(KF.guard("it works", QUESTION, CODE))

    def test_repeating_the_question_is_guarded(self):
        self.assertIsNotNone(KF.guard(QUESTION, QUESTION, CODE))

    def test_pasting_the_code_is_guarded(self):
        self.assertIsNotNone(KF.guard("\n".join(CODE.splitlines()[1:7]), QUESTION, CODE))

    def test_a_genuine_answer_is_not_guarded(self):
        self.assertIsNone(KF.guard(GOOD, QUESTION, CODE))
        self.assertIn("nothing from this code", KF.guard(VAGUE, QUESTION, CODE))  # a vague answer naming nothing of the code is not rated (by design)


class RelevanceAndPadding(unittest.TestCase):
    def test_an_answer_that_mentions_nothing_from_this_code_is_guarded(self):
        other = "The loader reads each record from the stream and validates the checksum before it hands the parsed block back to the caller for further processing."
        self.assertIn("nothing from this code", KF.guard(other, QUESTION, CODE, FACTS, "guard"))
        self.assertIn("nothing from this code", KF.guard("It takes the input, processes it step by step and returns the correct result as expected.", QUESTION, CODE, FACTS, "guard"))

    def test_repeating_one_word_is_guarded_as_padding(self):
        self.assertIn("padding", KF.guard(GOOD + " " + " ".join(["indeed"] * 40), QUESTION, CODE, FACTS, "guard"))

    def test_genuine_answers_are_not_caught_by_the_new_rules(self):
        self.assertIsNone(KF.guard(GOOD, QUESTION, CODE, FACTS, "guard"))
        self.assertIsNone(KF.guard("It checks the discount and raises when it is below zero, otherwise the total keeps going.", QUESTION, CODE, FACTS, "guard"))


class Features(unittest.TestCase):
    def test_naming_the_code_raises_identifier_recall_and_focus_overlap(self):
        good = KF.featurize(GOOD, QUESTION, CODE, FACTS, "guard")
        vague = KF.featurize(VAGUE, QUESTION, CODE, FACTS, "guard")
        self.assertGreater(good["identifier_recall"], vague["identifier_recall"])
        self.assertGreater(good["focus_overlap"], vague["focus_overlap"])
        self.assertEqual(good["exc_named"], 1.0)
        self.assertEqual(vague["exc_named"], 0.0)

    def test_features_cover_every_declared_name(self):
        self.assertEqual(set(KF.featurize(GOOD, QUESTION, CODE, FACTS, "guard")), set(KF.FEATURE_NAMES))

    def test_reference_text_comes_from_the_facts_only(self):
        r = KF.reference_text(FACTS, "cart_total")
        self.assertIn("raises ValueError when discount < 0", r)
        self.assertEqual(r, KF.reference_text(FACTS, "cart_total"))

    def test_unknown_question_type_still_works(self):
        self.assertEqual(KF.featurize(GOOD, QUESTION, CODE, FACTS)["focus_overlap"], 0.0)


class EntryPoint(unittest.TestCase):
    def payload(self, **kw):
        return {"student_response": GOOD, "code_snippet": CODE, "generated_question": QUESTION, "facts": FACTS, "file_path": "shop/cart.py", **kw}

    def test_no_answer_yet_is_not_available(self):
        with self.assertRaises(E.NotEnoughEvidence):
            E.evaluate(self.payload(student_response="  "))

    def test_no_code_is_not_available(self):
        with self.assertRaises(E.NotEnoughEvidence):
            E.evaluate(self.payload(code_snippet=""))

    def test_other_languages_are_not_scored_unless_allowed(self):
        with self.assertRaises(E.NotEnoughEvidence) as cm:
            E.evaluate(self.payload(file_path="src/cart.js", ast_metadata={"language": "other"}))
        self.assertIn("Python only", str(cm.exception))

    def test_a_timeout_is_a_real_zero(self):
        r = E.evaluate({"is_timeout": True})
        self.assertEqual(r["score"], 0.0)
        self.assertEqual(r["features"]["ko_raw_score"], 0.0)

    def test_missing_model_is_not_available_not_zero(self):
        old = S.MODEL_DIR
        S.MODEL_DIR = Path(tempfile.mkdtemp())
        try:
            with self.assertRaises(E.NotEnoughEvidence) as cm:
                E.evaluate(self.payload())
            self.assertIn("unavailable", str(cm.exception))
        finally:
            S.MODEL_DIR = old

    def test_feature_payloads_still_go_to_the_simulator(self):
        out = asyncio.run(E.async_evaluate({"code_snippet": CODE}, {"simulation_mode": "quick"}))
        self.assertIn("score", out)


class WholePathWithFakeEncoder(unittest.TestCase):
    """Fake encoder and fake head: checks the plumbing (feature sets, clipping, rating = 1 + 4 * score, guards skip the model), not accuracy."""

    def setUp(self):
        try:
            import joblib
            import numpy as np
            from sklearn.linear_model import Ridge
        except ImportError:
            self.skipTest("numpy / scikit-learn / joblib not installed")
        self.np = np
        self.dir = Path(tempfile.mkdtemp())
        fs = KF.feature_sets({k: np.ones((2, 4), "float32") / 2 for k in ("ans", "ques", "code", "ref", "joint")}, np.zeros((2, len(KF.FEATURE_NAMES))))
        X = fs["B+H"]
        joblib.dump(Ridge(alpha=1.0).fit(np.vstack([X, X + 0.1]), [0.2, 0.8, 0.3, 0.9]), self.dir / "ko_head.joblib")
        (self.dir / "ko_model.json").write_text(json.dumps({"encoder": "fake", "feature_set": "B+H", "head": "ridge", "residual_quantiles": [-0.1, 0.1]}), encoding="utf-8")
        self.old = S.MODEL_DIR
        S.MODEL_DIR = self.dir
        S._CACHE.clear()
        np_ = np

        class Fake:
            calls = 0

            def embed(self, texts):
                Fake.calls += 1
                v = np_.array([[(hash(t) % 97) / 97.0 + i for i in range(4)] for t in texts], "float32")
                return v / np_.linalg.norm(v, axis=1, keepdims=True)

        self.Fake = Fake

    def tearDown(self):
        S.MODEL_DIR = self.old
        S._CACHE.clear()

    def test_rating_is_one_plus_four_times_the_score_and_stays_in_range(self):
        r = S.rate(GOOD, QUESTION, CODE, FACTS, encoder=self.Fake(), qtype="guard")
        self.assertTrue(0.0 <= r["score"] <= 1.0)
        self.assertAlmostEqual(r["rating"], 1 + 4 * r["score"], places=2)
        self.assertLessEqual(r["interval"][0], r["score"] + 1e-9)
        self.assertGreaterEqual(r["interval"][1], r["score"] - 1e-9)

    def test_a_guarded_answer_is_rated_one_without_touching_the_encoder(self):
        enc = self.Fake()
        r = S.rate("ok", QUESTION, CODE, FACTS, encoder=enc)
        self.assertEqual((r["rating"], r["score"]), (1.0, 0.0))
        self.assertEqual(self.Fake.calls, 0)

    def test_the_entry_point_returns_the_standard_result(self):
        S._CACHE["fake"] = self.Fake()
        r = E.evaluate({"student_response": GOOD, "code_snippet": CODE, "generated_question": QUESTION, "facts": FACTS, "file_path": "a.py", "ast_metadata": {"language": "python", "question_type": "guard"}})
        for key in ("factor", "score", "interval", "features", "removed", "versions", "warnings"):
            self.assertIn(key, r)
        self.assertEqual(r["features"]["ko_raw_score"], r["score"])


if __name__ == "__main__":
    unittest.main()
