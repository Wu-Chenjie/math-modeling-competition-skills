import unittest

import model_prototype as mp


class ModelTests(unittest.TestCase):
    def test_simulation_is_deterministic_and_nonnegative(self):
        a = mp.simulate(species=4, years=30, drought_frequency=0.25, seed=7)
        b = mp.simulate(species=4, years=30, drought_frequency=0.25, seed=7)
        self.assertEqual(a["total"], b["total"])
        self.assertGreaterEqual(min(a["total"]), 0.0)

    def test_species_richness_metric_is_reported(self):
        out = mp.simulate(species=3, years=10, drought_frequency=0.2, seed=1)
        self.assertGreaterEqual(out["final_total"], 0.0)
        self.assertGreaterEqual(out["final_richness"], 0.0)
        self.assertLessEqual(out["final_richness"], 1.0)


if __name__ == "__main__":
    unittest.main()
