import tempfile
import unittest
from pathlib import Path

import model


class ModelTests(unittest.TestCase):
    def test_simulation_is_bounded_and_has_requested_horizon(self):
        trajectory = model.simulate(
            model.STRATEGIES["status_quo"], model.central_scenario(), years=30
        )
        self.assertEqual(31, len(trajectory))
        for row in trajectory:
            self.assertGreaterEqual(row["wildlife"], 0.0)
            self.assertLessEqual(row["wildlife"], 1.5)
            self.assertGreaterEqual(row["livelihood"], 0.0)
            self.assertLessEqual(row["livelihood"], 1.5)
            self.assertGreaterEqual(row["conflict"], 0.0)
            self.assertLessEqual(row["conflict"], 1.0)

    def test_scenario_grid_and_feasibility_are_deterministic(self):
        scenarios = model.scenario_grid()
        self.assertEqual(243, len(scenarios))
        self.assertTrue(all(model.is_feasible(s) for s in model.STRATEGIES.values()))

    def test_analysis_produces_pareto_set_and_expected_artifacts(self):
        analysis = model.analyze()
        self.assertIn("status_quo", analysis["strategy_metrics"])
        self.assertGreaterEqual(len(analysis["pareto_strategies"]), 1)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model.write_artifacts(root, {"problem_sha256": "test"}, "test-input")
            self.assertTrue((root / "results" / "metrics.json").exists())
            self.assertTrue((root / "results" / "reproducibility_manifest.json").exists())
            self.assertEqual(9, len(list((root / "figures").glob("*.svg"))))


if __name__ == "__main__":
    unittest.main()
