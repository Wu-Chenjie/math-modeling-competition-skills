import json
import pathlib
import unittest

import model_run


class ScenarioModelTests(unittest.TestCase):
    def test_evaluate_policy_respects_capacity_and_bounds(self):
        policy = {
            "name": "balanced",
            "wildlife": 0.80,
            "community": 0.75,
            "tourism": 0.70,
            "conflict": 0.25,
            "capacity": 0.60,
        }
        out = model_run.evaluate_policy(policy)
        self.assertGreaterEqual(out["composite"], 0.0)
        self.assertLessEqual(out["composite"], 1.0)
        self.assertLessEqual(out["capacity_use"], 1.0)

    def test_summary_has_no_empirical_rows(self):
        summary = model_run.load_summary(model_run.DEFAULT_INPUT)
        self.assertEqual(summary["data_files"], [])
        self.assertEqual(summary["data_audit"], [])


if __name__ == "__main__":
    unittest.main()
