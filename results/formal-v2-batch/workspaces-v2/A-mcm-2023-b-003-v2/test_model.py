import unittest

import model


class ModelTests(unittest.TestCase):
    def test_candidate_grid_is_deterministic_and_nonempty(self):
        first = model.evaluate_all_candidates()
        second = model.evaluate_all_candidates()
        self.assertEqual(first, second)
        self.assertGreater(len(first), 100)

    def test_all_candidates_respect_declared_bounds_and_capacity(self):
        for candidate in model.evaluate_all_candidates():
            self.assertTrue(model.is_feasible(candidate["decision"]))
            for scenario in candidate["scenario_outcomes"].values():
                self.assertLessEqual(scenario["visitation"], scenario["effective_capacity"] + 1e-12)
                for objective in model.OBJECTIVES:
                    self.assertGreaterEqual(scenario[objective], 0.0)
                    self.assertLessEqual(scenario[objective], 1.0)

    def test_recommendation_is_pareto_efficient(self):
        result = model.run_analysis()
        recommended_id = result["recommendation"]["candidate_id"]
        pareto_ids = {row["candidate_id"] for row in result["pareto_front"]}
        self.assertIn(recommended_id, pareto_ids)

    def test_report_has_all_preregistered_sections(self):
        report = model.build_report(model.run_analysis())
        required = {
            "problem_framing",
            "data_audit",
            "assumptions",
            "candidate_models",
            "baseline",
            "math_specification",
            "code_prototype",
            "experiment",
            "validation",
            "sensitivity_robustness",
            "falsification",
            "reviewer_risks",
            "reproducibility_manifest",
        }
        self.assertEqual(required, set(report))
        self.assertEqual(report["data_audit"]["observed_rows"], 0)
        self.assertTrue(report["data_audit"]["model_generated_values_only"])


if __name__ == "__main__":
    unittest.main()
