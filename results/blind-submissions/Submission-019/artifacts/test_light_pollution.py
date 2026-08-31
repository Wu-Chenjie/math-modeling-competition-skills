import unittest

from light_pollution_model import score_risk, apply_intervention, rank_interventions


class LightPollutionModelTests(unittest.TestCase):
    def test_score_risk_is_weighted_and_bounded(self):
        components = {"skyglow": 1.0, "trespass": 0.0, "glare": 0.0, "ecology": 0.0, "human": 0.0}
        self.assertAlmostEqual(score_risk(components), 30.0)

    def test_intervention_reduces_targeted_components(self):
        components = {"skyglow": 0.8, "trespass": 0.8, "glare": 0.8, "ecology": 0.8, "human": 0.8}
        updated = apply_intervention(components, "shielding")
        self.assertLess(score_risk(updated), score_risk(components))

    def test_rank_interventions_returns_lowest_post_action_risk_first(self):
        components = {"skyglow": 0.8, "trespass": 0.8, "glare": 0.8, "ecology": 0.8, "human": 0.8}
        ranked = rank_interventions(components)
        self.assertEqual(ranked[0][1], min(risk for _, risk in ranked))


if __name__ == "__main__":
    unittest.main()
