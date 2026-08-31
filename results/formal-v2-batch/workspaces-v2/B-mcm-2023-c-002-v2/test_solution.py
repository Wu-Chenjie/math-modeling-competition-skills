import json
import math
import unittest

import solution


class ModelingPipelineTests(unittest.TestCase):
    def test_excel_serial_conversion(self):
        self.assertEqual(solution.excel_date(44926).isoformat(), "2022-12-31")

    def test_composition_is_closed(self):
        values = solution.close_composition([1, 2, 3, 4, 5, 6, 7])
        self.assertAlmostEqual(sum(values), 100.0, places=10)
        self.assertTrue(all(value > 0 for value in values))

    def test_linear_solver_recovers_known_coefficients(self):
        x = [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0], [1.0, 3.0]]
        y = [2.0, 5.0, 8.0, 11.0]
        beta = solution.ridge_fit(x, y, penalty=0.0)
        self.assertAlmostEqual(beta[0], 2.0, places=8)
        self.assertAlmostEqual(beta[1], 3.0, places=8)

    def test_softmax_prediction_is_valid(self):
        prediction = solution.alr_inverse([0.0] * 6)
        self.assertEqual(len(prediction), 7)
        self.assertAlmostEqual(sum(prediction), 100.0, places=10)
        self.assertTrue(all(math.isfinite(value) and value > 0 for value in prediction))

    def test_metrics_contract(self):
        required = {
            "problem_framing", "data_audit", "assumptions", "candidate_models",
            "baseline", "math_specification", "code_prototype", "experiment",
            "validation", "sensitivity_robustness", "falsification",
            "reviewer_risks", "reproducibility_manifest"
        }
        if solution.METRICS_PATH.exists():
            payload = json.loads(solution.METRICS_PATH.read_text(encoding="utf-8"))
            self.assertTrue(required.issubset(payload))


if __name__ == "__main__":
    unittest.main()
