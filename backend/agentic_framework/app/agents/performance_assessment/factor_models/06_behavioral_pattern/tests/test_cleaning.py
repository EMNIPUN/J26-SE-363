"""Run from factor_models/:  python -m unittest discover -s 06_behavioral_pattern/tests"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE.parents[1]))

from cleaning import validate_inputs  # noqa: E402
from evidence.lines import CLEANING_VERSION  # noqa: E402


class BehaviouralPatternInputs(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(validate_inputs({"E": 0.5, "C": 0.4, "Co": 0.2}, {"C_bimodal": 0}, {"effort": CLEANING_VERSION, "consistency": CLEANING_VERSION}))

    def test_out_of_range_and_missing(self):
        with self.assertRaises(ValueError):
            validate_inputs({"E": 1.4, "C": 0.4}, {"C_bimodal": 0})

    def test_mixed_versions_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_inputs({"E": 0.5, "C": 0.4, "Co": 0.2}, {"C_bimodal": 1}, {"effort": "1.0.0", "consistency": "0.9.0"})


if __name__ == "__main__":
    unittest.main()
