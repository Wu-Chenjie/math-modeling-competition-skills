import json
import unittest
from pathlib import Path

import run_model


class ModelContractTests(unittest.TestCase):
    def test_network_has_17_goals_and_deterministic_priorities(self):
        graph = run_model.build_prior_graph()
        self.assertEqual(len(graph["names"]), 17)
        self.assertEqual(len(graph["edges"]), len(set(graph["edges"])))
        first = run_model.rank_goals(graph)
        second = run_model.rank_goals(run_model.build_prior_graph())
        self.assertEqual(first["ranking"], second["ranking"])
        self.assertEqual(len(first["ranking"]), 17)

    def test_scenario_and_output_contract(self):
        graph = run_model.build_prior_graph()
        base = run_model.rank_goals(graph)
        scenario = run_model.remove_goal_scenario(graph, 1)
        changed = run_model.rank_goals(scenario)
        self.assertEqual(len(changed["ranking"]), 16)
        self.assertNotEqual(base["ranking"][:5], changed["ranking"][:5])

    def test_svg_and_json_are_written(self):
        out = run_model.run_experiment(Path("test_artifacts"))
        self.assertGreaterEqual(len(out["figures"]), 9)
        self.assertTrue(Path(out["metrics_path"]).exists())
        payload = json.loads(Path(out["metrics_path"]).read_text(encoding="utf-8"))
        self.assertIn("report", payload)
        self.assertEqual(payload["report"]["data_audit"]["rows_available"], 0)


if __name__ == "__main__":
    unittest.main()
