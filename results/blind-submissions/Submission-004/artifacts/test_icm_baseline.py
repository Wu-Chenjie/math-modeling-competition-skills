import json
import unittest
from pathlib import Path

from icm_baseline import load_case, build_baseline


CASE_PATH = Path(r"C:/Users/伍辰杰/Documents/ChatGPT/mathmodel/math-modeling-competition-skills/benchmarks/case-summaries/icm-2023-d.json")


class BaselineTests(unittest.TestCase):
    def test_empty_audit_yields_equal_weight_baseline(self):
        case = load_case(CASE_PATH)
        result = build_baseline(case)
        self.assertEqual(result["n_goals"], 17)
        self.assertEqual(result["data_rows"], 0)
        self.assertEqual(result["weights_sum"], 1.0)
        self.assertEqual(len(result["ranking"]), 17)
        self.assertTrue(all(abs(row["priority"] - 1 / 17) < 1e-12 for row in result["ranking"]))
        self.assertTrue(result["pending_stages"])


if __name__ == "__main__":
    unittest.main()
