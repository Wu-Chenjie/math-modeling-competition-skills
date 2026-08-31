import math
import unittest
from dataclasses import replace

from model import Scenario, simulate, traits


class PublicModelTests(unittest.TestCase):
    def test_replay_is_deterministic(self):
        self.assertEqual(simulate(Scenario(), 41, 30)["trajectory"], simulate(Scenario(), 41, 30)["trajectory"])

    def test_biomass_is_finite_and_nonnegative(self):
        values = simulate(Scenario(), 42, 80)["trajectory"]
        self.assertTrue(all(math.isfinite(v) and v >= 0 for v in values))

    def test_zero_drought_probability_has_no_drought(self):
        result = simulate(replace(Scenario(), drought_probability=0.0), 43, 50)
        self.assertEqual(sum(result["drought"]), 0)

    def test_extreme_stress_does_not_improve_terminal_biomass(self):
        base = simulate(replace(Scenario(), drought_probability=0.0), 44, 50)
        stressed = simulate(replace(Scenario(), drought_probability=1.0, pollution=0.8, habitat_fraction=0.1), 44, 50)
        self.assertLessEqual(stressed["terminal_biomass"], base["terminal_biomass"])

    def test_trait_count_matches_richness(self):
        self.assertEqual(len(traits(9, "mixed")), 9)


if __name__ == "__main__":
    unittest.main()
