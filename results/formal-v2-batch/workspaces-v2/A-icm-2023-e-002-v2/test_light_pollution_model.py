import json
import tempfile
import unittest
from pathlib import Path

import light_pollution_model as model


class RiskModelTests(unittest.TestCase):
    def test_scores_are_bounded(self):
        for location in model.scenario_locations():
            score = model.risk_score(location, model.INTERVENTIONS["baseline"])
            self.assertGreaterEqual(score["risk_score"], 0.0)
            self.assertLessEqual(score["risk_score"], 100.0)

    def test_more_pressure_does_not_reduce_risk(self):
        location = model.scenario_locations()[0]
        worse = dict(location)
        for key in model.PRESSURE_KEYS:
            worse[key] = min(1.0, location[key] + 0.1)
        base = model.risk_score(location, model.INTERVENTIONS["baseline"])
        raised = model.risk_score(worse, model.INTERVENTIONS["baseline"])
        self.assertGreaterEqual(raised["risk_score"], base["risk_score"])

    def test_intervention_results_cover_all_scenarios(self):
        rows = model.evaluate_scenarios()
        expected = len(model.scenario_locations()) * len(model.INTERVENTIONS)
        self.assertEqual(len(rows), expected)
        self.assertTrue(all(row["input_provenance"] == "synthetic_scenario_assumption" for row in rows))

    def test_sensitivity_is_deterministic(self):
        first = model.run_sensitivity(draws=50, seed=2023)
        second = model.run_sensitivity(draws=50, seed=2023)
        self.assertEqual(first, second)

    def test_pipeline_writes_machine_readable_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            model.run_pipeline(output, draws=20)
            payload = json.loads((output / "results" / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["case_id"], "icm-2023-e")
            self.assertFalse(payload["data_audit"]["empirical_data_available"])
            self.assertIn("pending_stages", payload)


if __name__ == "__main__":
    unittest.main()
