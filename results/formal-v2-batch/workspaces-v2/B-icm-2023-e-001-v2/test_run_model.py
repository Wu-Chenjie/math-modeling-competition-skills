import unittest

import run_model


class RiskModelTests(unittest.TestCase):
    def test_score_is_bounded_at_endpoints(self):
        weights = [0.2] * 5
        self.assertEqual(run_model.risk_score([0.0] * 5, weights), 0.0)
        self.assertEqual(run_model.risk_score([1.0] * 5, weights), 100.0)

    def test_score_is_monotone_in_each_component(self):
        weights = [0.2] * 5
        lower = run_model.risk_score([0.2] * 5, weights)
        higher = run_model.risk_score([0.2, 0.2, 0.7, 0.2, 0.2], weights)
        self.assertGreater(higher, lower)

    def test_interventions_do_not_increase_components(self):
        location = [0.9, 0.8, 0.4, 0.7, 0.8]
        for reductions in run_model.INTERVENTIONS.values():
            treated = run_model.apply_intervention(location, reductions)
            self.assertTrue(all(0.0 <= after <= before for before, after in zip(location, treated)))


if __name__ == "__main__":
    unittest.main()
