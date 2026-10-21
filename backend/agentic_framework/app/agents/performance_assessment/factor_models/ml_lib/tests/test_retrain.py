"""Run from factor_models/ml_lib:  python -m unittest discover -s tests"""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import retrain as R  # noqa: E402


def frame(configs, outers=("A", "B"), inners=("C", "D", "E")):
    """configs: {sid: error added to a perfect prediction}. Two records per combination."""
    rows = []
    for sid, err in configs.items():
        for o in outers:
            for v in inners:
                for k in range(2):
                    rows.append(("Ridge", "v", "rated only", 1.0, sid, o, v, f"{o}{v}{k}", 0.5, 0.5 + err))
    return pd.DataFrame(rows, columns=["model", "variant", "lab", "weight", "sid", "outer_test", "inner_val", "record_id", "y", "pred"])


class Selection(unittest.TestCase):
    def test_bias_free_picks_the_best_on_the_other_groups(self):
        tp = frame({0: 0.10, 1: 0.02, 2: 0.30})
        out, chosen = R.bias_free(tp)
        self.assertTrue(all(pick[2] == 1 for pick in chosen.values()))
        self.assertAlmostEqual((out.pred - out.y).abs().mean(), 0.02)

    def test_bias_free_does_not_look_at_the_scored_group(self):
        # config 1 is great everywhere except in group C, where it is terrible; the choice for C must ignore C
        tp = frame({0: 0.10, 1: 0.02})
        tp.loc[(tp.sid == 1) & (tp.inner_val == "C"), "pred"] = 0.5 + 0.9
        out, chosen = R.bias_free(tp)
        self.assertEqual(chosen[("A", "C")][2], 1)  # chosen on D and E, where config 1 wins
        scored_c = out[(out.outer_test == "A") & (out.inner_val == "C")]
        self.assertGreater((scored_c.pred - scored_c.y).abs().mean(), 0.5)  # and it is then scored honestly on C

    def test_complexity_orders_simpler_first(self):
        self.assertLess(R.complexity("Ridge", {"alpha": 100.0}), R.complexity("Ridge", {"alpha": 0.01}))
        shallow = {"n_estimators": 100, "max_depth": 2, "min_samples_leaf": 5, "max_features": 1.0}
        deep = {"n_estimators": 300, "max_depth": None, "min_samples_leaf": 1, "max_features": 1.0}
        self.assertLess(R.complexity("Random Forest", shallow), R.complexity("Random Forest", deep))

    def test_settings_are_reproducible(self):
        self.assertEqual(R.make_settings(), R.make_settings())

    def test_effort_guard(self):
        spam = pd.DataFrame([{"E_CC": 200, "E_LOC_net_capped": 200, "E_FC": 2}])
        g = R.apply_guard(spam)
        self.assertEqual(g.E_CC.iloc[0], 2.0)  # 200 commits carrying 200 lines are worth 2 commits
        dump = pd.DataFrame([{"E_CC": 1, "E_LOC_net_capped": 800, "E_FC": 1000}])
        self.assertEqual(R.apply_guard(dump).E_FC.iloc[0], 20.0)


if __name__ == "__main__":
    unittest.main()
